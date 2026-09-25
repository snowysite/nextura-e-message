from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from flask_socketio import (
    SocketIO,
    join_room,
    emit
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime

import sqlite3
import os
import base64


# =========================================================
# APP SETUP
# =========================================================

app = Flask(__name__)

app.secret_key = "nextura_secret_key"


socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


login_manager = LoginManager(app)

login_manager.login_view = "login"


# =========================================================
# FOLDERS
# =========================================================

AVATAR_FOLDER = "static/uploads/avatars"

VOICE_FOLDER = "static/uploads/voices"


os.makedirs(
    AVATAR_FOLDER,
    exist_ok=True
)

os.makedirs(
    VOICE_FOLDER,
    exist_ok=True
)


# =========================================================
# ONLINE USERS
# =========================================================

online_users = set()


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(
        "database.db",
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    db = get_db()


    # -------------------------
    # USERS
    # -------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            profile_image TEXT
                DEFAULT 'default.png'
        )
    """)


    # -------------------------
    # MESSAGES
    # -------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender_id INTEGER NOT NULL,

            receiver_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            message_type TEXT
                DEFAULT 'text',

            timestamp DATETIME
                DEFAULT CURRENT_TIMESTAMP,

            status TEXT
                DEFAULT 'sent'
        )
    """)


    # -------------------------
    # NOTIFICATIONS
    # -------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            sender_id INTEGER NOT NULL,

            message TEXT,

            is_read INTEGER
                DEFAULT 0,

            created_at DATETIME
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # =====================================================
    # MESSAGE REPLY MIGRATION
    # =====================================================

    message_columns = db.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()

    message_column_names = [
        column["name"]
        for column in message_columns
    ]

    if "reply_to_id" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN reply_to_id INTEGER
        """)

        print(
            "✅ Added reply_to_id column to messages table."
        )


    db.commit()

    db.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def get_room_id(u1, u2):

    u1 = int(u1)

    u2 = int(u2)

    return (
        f"chat_{min(u1, u2)}_"
        f"{max(u1, u2)}"
    )


# =========================================================
# GET REPLY INFORMATION
# =========================================================

def get_reply_info(
    db,
    reply_to_id,
    sender_id,
    receiver_id
):

    """
    Validates that the reply target belongs to the
    current conversation.

    Returns:

        reply_to_id
        reply_preview
        reply_sender_name
    """

    if reply_to_id in (
        None,
        "",
        "null",
        "undefined"
    ):

        return (
            None,
            None,
            None
        )


    try:

        reply_to_id = int(
            reply_to_id
        )

    except (
        TypeError,
        ValueError
    ):

        return (
            None,
            None,
            None
        )


    reply_message = db.execute("""
        SELECT

            messages.id,

            messages.sender_id,

            messages.receiver_id,

            messages.message,

            messages.message_type,

            users.username AS sender_name

        FROM messages

        LEFT JOIN users
            ON users.id = messages.sender_id

        WHERE messages.id = ?

        AND (

            (
                messages.sender_id = ?
                AND
                messages.receiver_id = ?
            )

            OR

            (
                messages.sender_id = ?
                AND
                messages.receiver_id = ?
            )

        )

    """, (
        reply_to_id,

        sender_id,
        receiver_id,

        receiver_id,
        sender_id
    )).fetchone()


    if not reply_message:

        return (
            None,
            None,
            None
        )


    # -----------------------------------------
    # Create preview
    # -----------------------------------------

    if reply_message["message_type"] == "voice":

        reply_preview = "🎙 Voice message"

    else:

        reply_preview = (
            reply_message["message"]
            or ""
        )


    # -----------------------------------------
    # Sender name
    # -----------------------------------------

    reply_sender_name = (
        reply_message["sender_name"]
        or "User"
    )


    return (
        reply_message["id"],
        reply_preview,
        reply_sender_name
    )


# =========================================================
# CREATE NOTIFICATION
# =========================================================

def create_notification(
    receiver_id,
    sender_id,
    message
):

    """
    Creates a notification in the database
    and immediately sends it to the receiver
    through Socket.IO.
    """

    db = get_db()


    # -----------------------------------------
    # Save notification
    # -----------------------------------------

    cursor = db.execute("""
        INSERT INTO notifications
        (
            user_id,
            sender_id,
            message
        )
        VALUES (?, ?, ?)
    """, (
        receiver_id,
        sender_id,
        message
    ))


    notification_id = cursor.lastrowid


    # -----------------------------------------
    # Get sender username
    # -----------------------------------------

    sender = db.execute("""
        SELECT username
        FROM users
        WHERE id = ?
    """, (
        sender_id,
    )).fetchone()


    sender_name = (
        sender["username"]
        if sender
        else "Someone"
    )


    db.commit()

    db.close()


    # -----------------------------------------
    # Send real-time notification
    # -----------------------------------------

    socketio.emit(
        "new_notification",
        {
            "id": notification_id,

            "sender_id": sender_id,

            "sender_name": sender_name,

            "receiver_id": receiver_id,

            "message": message
        },

        room=f"user_{receiver_id}"
    )


# =========================================================
# USER MODEL
# =========================================================

class User(UserMixin):

    def __init__(
        self,
        id,
        username,
        email,
        password,
        profile_image="default.png"
    ):

        self.id = id

        self.username = username

        self.email = email

        self.password = password

        self.profile_image = profile_image


# =========================================================
# FLASK LOGIN
# =========================================================

@login_manager.user_loader
def load_user(user_id):

    db = get_db()


    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (
            user_id,
        )
    ).fetchone()


    db.close()


    if user:

        return User(
            user["id"],
            user["username"],
            user["email"],
            user["password"],
            user["profile_image"]
        )


    return None


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )


    return redirect(
        url_for("login")
    )


# =========================================================
# SIGNUP
# =========================================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        if not username or not email or not password:

            flash(
                "Please fill in all fields."
            )

            return render_template(
                "signup.html"
            )


        db = get_db()


        try:

            db.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password
                )
                VALUES (?, ?, ?)
                """,
                (
                    username,

                    email,

                    generate_password_hash(
                        password
                    )
                )
            )


            db.commit()


            flash(
                "Account created successfully. Please login."
            )


            return redirect(
                url_for("login")
            )


        except sqlite3.IntegrityError:

            flash(
                "Username or email already exists."
            )


        except Exception as e:

            print(
                "Signup error:",
                e
            )

            flash(
                "Something went wrong while creating your account."
            )


        finally:

            db.close()


    return render_template(
        "signup.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        db = get_db()


        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (
                email,
            )
        ).fetchone()


        db.close()


        if user and check_password_hash(
            user["password"],
            password
        ):

            login_user(
                User(
                    user["id"],
                    user["username"],
                    user["email"],
                    user["password"],
                    user["profile_image"]
                )
            )


            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid login details."
        )


    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()


    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",

        username=current_user.username
    )


# =========================================================
# USERS
# =========================================================

@app.route("/users")
@login_required
def users():

    db = get_db()


    users = db.execute(
        """
        SELECT
            id,
            username,
            profile_image
        FROM users
        WHERE id != ?
        """,
        (
            current_user.id,
        )
    ).fetchall()


    db.close()


    return render_template(
        "users.html",

        users=users,

        online_users=online_users
    )


# =========================================================
# NOTIFICATION API
# =========================================================

@app.route("/api/notifications")
@login_required
def get_notifications():

    db = get_db()


    # -----------------------------------------
    # Get notifications
    # -----------------------------------------

    notifications = db.execute("""
        SELECT

            notifications.id,

            notifications.sender_id,

            notifications.message,

            notifications.is_read,

            notifications.created_at,

            users.username AS sender_name

        FROM notifications

        LEFT JOIN users
            ON users.id =
               notifications.sender_id

        WHERE notifications.user_id = ?

        ORDER BY
            notifications.created_at DESC

        LIMIT 50

    """, (
        current_user.id,
    )).fetchall()


    # -----------------------------------------
    # Get unread count
    # -----------------------------------------

    unread = db.execute("""
        SELECT COUNT(*) AS count

        FROM notifications

        WHERE user_id = ?

        AND is_read = 0

    """, (
        current_user.id,
    )).fetchone()


    db.close()


    return jsonify({

        "success": True,

        "unread_count":
            unread["count"],

        "notifications": [

            {
                "id":
                    notification["id"],

                "sender_id":
                    notification["sender_id"],

                "sender_name":
                    notification["sender_name"]
                    or "Someone",

                "message":
                    notification["message"]
                    or "New message",

                "is_read":
                    notification["is_read"],

                "created_at":
                    notification["created_at"]
            }

            for notification
            in notifications
        ]
    })


# =========================================================
# MARK NOTIFICATIONS AS READ
# =========================================================

@app.route(
    "/api/notifications/read",
    methods=["POST"]
)
@login_required
def mark_notifications_read():

    db = get_db()


    db.execute("""
        UPDATE notifications

        SET is_read = 1

        WHERE user_id = ?

    """, (
        current_user.id,
    ))


    db.commit()

    db.close()


    return jsonify({

        "success": True,

        "message":
            "Notifications marked as read."
    })


# =========================================================
# CHAT PAGE
# =========================================================

@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):

    db = get_db()


    # -----------------------------------------
    # Get receiver
    # -----------------------------------------

    receiver = db.execute(
        """
        SELECT

            id,

            username,

            profile_image

        FROM users

        WHERE id = ?

        """,
        (
            user_id,
        )
    ).fetchone()


    if not receiver:

        db.close()


        flash(
            "User not found."
        )


        return redirect(
            url_for("users")
        )


    # -----------------------------------------
    # Get messages
    # -----------------------------------------

    messages = db.execute("""
        SELECT *

        FROM messages

        WHERE

            (
                sender_id = ?

                AND

                receiver_id = ?
            )

            OR

            (
                sender_id = ?

                AND

                receiver_id = ?
            )

        ORDER BY
            timestamp ASC

    """, (
        current_user.id,

        user_id,

        user_id,

        current_user.id
    )).fetchall()


    # -----------------------------------------
    # Mark notifications from this user
    # as read
    # -----------------------------------------

    db.execute("""
        UPDATE notifications

        SET is_read = 1

        WHERE user_id = ?

        AND sender_id = ?

    """, (
        current_user.id,

        user_id
    ))


    db.commit()

    db.close()


    return render_template(
        "chat.html",

        receiver=receiver,

        messages=messages,

        my_id=current_user.id
    )


# =========================================================
# SOCKET.IO CONNECTION
# =========================================================

@socketio.on("connect")
def connect():

    if not current_user.is_authenticated:

        return


    # -----------------------------------------
    # Join personal notification room
    # -----------------------------------------

    join_room(
        f"user_{current_user.id}"
    )


    # -----------------------------------------
    # Add user online
    # -----------------------------------------

    online_users.add(
        current_user.id
    )


    # -----------------------------------------
    # Broadcast online users
    # -----------------------------------------

    emit(
        "status_update",

        list(online_users),

        broadcast=True
    )


# =========================================================
# SOCKET.IO DISCONNECT
# =========================================================

@socketio.on("disconnect")
def disconnect():

    if not current_user.is_authenticated:

        return


    online_users.discard(
        current_user.id
    )


    emit(
        "status_update",

        list(online_users),

        broadcast=True
    )


# =========================================================
# JOIN CHAT ROOM
# =========================================================

@socketio.on("join")
def on_join(data):

    if not current_user.is_authenticated:

        return


    sender_id = current_user.id


    receiver_id = data.get(
        "receiver_id"
    )


    if not receiver_id:

        return


    try:

        receiver_id = int(
            receiver_id
        )

    except (TypeError, ValueError):

        return


    # -----------------------------------------
    # Join private chat room
    # -----------------------------------------

    join_room(
        get_room_id(
            sender_id,
            receiver_id
        )
    )


# =========================================================
# SEND TEXT MESSAGE
# =========================================================

@socketio.on("send_message")
def send_message(data):

    if not current_user.is_authenticated:

        return


    # -----------------------------------------
    # Sender
    # -----------------------------------------

    sender_id = current_user.id


    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    try:

        receiver_id = int(
            data.get("receiver_id")
        )

    except (TypeError, ValueError):

        return


    # -----------------------------------------
    # Message
    # -----------------------------------------

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()


    if not message:

        return


    # -----------------------------------------
    # Prevent messaging yourself
    # -----------------------------------------

    if sender_id == receiver_id:

        return


    # -----------------------------------------
    # Reply message ID
    # -----------------------------------------

    reply_to_id = data.get(
        "reply_to_id"
    )


    db = get_db()


    # -----------------------------------------
    # Verify receiver exists
    # -----------------------------------------

    receiver = db.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        """,
        (
            receiver_id,
        )
    ).fetchone()


    if not receiver:

        db.close()

        return


    # -----------------------------------------
    # Validate reply target
    # -----------------------------------------

    (
        reply_to_id,
        reply_preview,
        reply_sender_name
    ) = get_reply_info(
        db,
        reply_to_id,
        sender_id,
        receiver_id
    )


    # -----------------------------------------
    # Save message
    # -----------------------------------------

    cursor = db.execute("""
        INSERT INTO messages

        (
            sender_id,

            receiver_id,

            message,

            message_type,

            status,

            reply_to_id
        )

        VALUES
        (
            ?,
            ?,
            ?,
            'text',
            'sent',
            ?
        )

    """, (
        sender_id,

        receiver_id,

        message,

        reply_to_id
    ))


    message_id = cursor.lastrowid


    db.commit()

    db.close()


    # -----------------------------------------
    # Send message to chat
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        {
            "id": message_id,

            "sender_id": sender_id,

            "receiver_id": receiver_id,

            "message": message,

            "message_type": "text",

            "status": "sent",

            "reply_to_id": reply_to_id,

            "reply_preview": reply_preview,

            "reply_sender_name": reply_sender_name
        },

        room=get_room_id(
            sender_id,
            receiver_id
        )
    )


    # -----------------------------------------
    # Create notification
    # -----------------------------------------

    create_notification(
        receiver_id,
        sender_id,
        message
    )


# =========================================================
# SEND VOICE MESSAGE
# =========================================================

@socketio.on("send_voice")
def send_voice(data):

    if not current_user.is_authenticated:

        return


    sender_id = current_user.id


    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    try:

        receiver_id = int(
            data.get("receiver_id")
        )

    except (TypeError, ValueError):

        return


    # -----------------------------------------
    # Prevent sending to yourself
    # -----------------------------------------

    if sender_id == receiver_id:

        return


    # -----------------------------------------
    # Audio data
    # -----------------------------------------

    audio_data = data.get(
        "audio"
    )


    if not audio_data:

        return


    # -----------------------------------------
    # Reply message ID
    # -----------------------------------------

    reply_to_id = data.get(
        "reply_to_id"
    )


    # -----------------------------------------
    # Verify receiver and reply
    # -----------------------------------------

    db = get_db()


    receiver = db.execute("""
        SELECT id
        FROM users
        WHERE id = ?
    """, (
        receiver_id,
    )).fetchone()


    if not receiver:

        db.close()

        return


    (
        reply_to_id,
        reply_preview,
        reply_sender_name
    ) = get_reply_info(
        db,
        reply_to_id,
        sender_id,
        receiver_id
    )


    db.close()


    # -----------------------------------------
    # Decode audio data
    # -----------------------------------------

    try:

        if "," in audio_data:

            audio_base64 = audio_data.split(
                ",",
                1
            )[1]

        else:

            audio_base64 = audio_data


        audio_bytes = base64.b64decode(
            audio_base64
        )

    except Exception as e:

        print(
            "Voice decode error:",
            e
        )

        return


    # -----------------------------------------
    # Filename
    # -----------------------------------------

    filename = (
        f"{sender_id}_"
        f"{int(datetime.utcnow().timestamp())}_"
        f"{os.urandom(4).hex()}.webm"
    )


    path = os.path.join(
        VOICE_FOLDER,
        filename
    )


    # -----------------------------------------
    # Save voice file
    # -----------------------------------------

    try:

        with open(
            path,
            "wb"
        ) as audio_file:

            audio_file.write(
                audio_bytes
            )

    except Exception as e:

        print(
            "Voice save error:",
            e
        )

        return


    # -----------------------------------------
    # Save voice message
    # -----------------------------------------

    db = get_db()


    cursor = db.execute("""
        INSERT INTO messages

        (
            sender_id,

            receiver_id,

            message,

            message_type,

            status,

            reply_to_id
        )

        VALUES
        (
            ?,
            ?,
            ?,
            'voice',
            'sent',
            ?
        )

    """, (
        sender_id,

        receiver_id,

        filename,

        reply_to_id
    ))


    message_id = cursor.lastrowid


    db.commit()

    db.close()


    # -----------------------------------------
    # Voice URL
    # -----------------------------------------

    audio_url = url_for(
        "static",
        filename=
            f"uploads/voices/{filename}"
    )


    # -----------------------------------------
    # Send voice message
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        {
            "id": message_id,

            "sender_id": sender_id,

            "receiver_id": receiver_id,

            "message": filename,

            "audio": audio_url,

            "message_type": "voice",

            "status": "sent",

            "reply_to_id": reply_to_id,

            "reply_preview": reply_preview,

            "reply_sender_name": reply_sender_name
        },

        room=get_room_id(
            sender_id,
            receiver_id
        )
    )


    # -----------------------------------------
    # Create notification
    # -----------------------------------------

    create_notification(
        receiver_id,
        sender_id,
        "🎙 Voice message"
    )


# =========================================================
# AUDIO CALL
# =========================================================

@socketio.on("call_user")
def call_user(data):

    if not current_user.is_authenticated:

        return


    target = data.get(
        "target"
    )


    offer = data.get(
        "offer"
    )


    if not target or not offer:

        return


    emit(
        "incoming_call",

        {
            "from":
                current_user.id,

            "offer":
                offer
        },

        room=f"user_{target}"
    )


# =========================================================
# CALL ACCEPTED
# =========================================================

@socketio.on("call_accepted")
def call_accepted(data):

    if not current_user.is_authenticated:

        return


    target = data.get(
        "target"
    )


    answer = data.get(
        "answer"
    )


    if not target or not answer:

        return


    emit(
        "call_accepted",

        {
            "answer":
                answer
        },

        room=f"user_{target}"
    )


# =========================================================
# ICE CANDIDATE
# =========================================================

@socketio.on("ice_candidate")
def ice_candidate(data):

    if not current_user.is_authenticated:

        return


    target = data.get(
        "target"
    )


    candidate = data.get(
        "candidate"
    )


    if not target or not candidate:

        return


    emit(
        "ice_candidate",

        {
            "candidate":
                candidate
        },

        room=f"user_{target}"
    )


# =========================================================
# END CALL
# =========================================================

@socketio.on("end_call")
def end_call(data):

    if not current_user.is_authenticated:

        return


    target = data.get(
        "target"
    )


    if not target:

        return


    emit(
        "call_ended",

        room=f"user_{target}"
    )


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    socketio.run(
        app,
        debug=False,
        host="0.0.0.0",
        port=port
    )