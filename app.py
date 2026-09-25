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
    # MESSAGE MIGRATIONS
    # =====================================================

    message_columns = db.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()

    message_column_names = [
        column["name"]
        for column in message_columns
    ]

    # -----------------------------------------------------
    # REPLY TO ID
    # -----------------------------------------------------

    if "reply_to_id" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN reply_to_id INTEGER
        """)

        print(
            "✅ Added reply_to_id column to messages table."
        )

        message_column_names.append(
            "reply_to_id"
        )

    # -----------------------------------------------------
    # DELETE FOR SENDER
    # -----------------------------------------------------

    if "deleted_for_sender" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN deleted_for_sender INTEGER
            DEFAULT 0
        """)

        print(
            "✅ Added deleted_for_sender column."
        )

        message_column_names.append(
            "deleted_for_sender"
        )

    # -----------------------------------------------------
    # DELETE FOR RECEIVER
    # -----------------------------------------------------

    if "deleted_for_receiver" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN deleted_for_receiver INTEGER
            DEFAULT 0
        """)

        print(
            "✅ Added deleted_for_receiver column."
        )

        message_column_names.append(
            "deleted_for_receiver"
        )

    # -----------------------------------------------------
    # DELETE FOR EVERYONE
    # -----------------------------------------------------

    if "deleted_for_everyone" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN deleted_for_everyone INTEGER
            DEFAULT 0
        """)

        print(
            "✅ Added deleted_for_everyone column."
        )

        message_column_names.append(
            "deleted_for_everyone"
        )

    # -----------------------------------------------------
    # PHASE 2.3 — EDITED
    # -----------------------------------------------------

    if "edited" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN edited INTEGER
            DEFAULT 0
        """)

        print(
            "✅ Added edited column."
        )

        message_column_names.append(
            "edited"
        )

    # -----------------------------------------------------
    # PHASE 2.3 — EDITED AT
    # -----------------------------------------------------

    if "edited_at" not in message_column_names:

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN edited_at DATETIME
        """)

        print(
            "✅ Added edited_at column."
        )

        message_column_names.append(
            "edited_at"
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

            messages.deleted_for_everyone,

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
    # Deleted message preview
    # -----------------------------------------

    if reply_message["deleted_for_everyone"]:

        reply_preview = "🚫 This message was deleted"

    # -----------------------------------------
    # Voice preview
    # -----------------------------------------

    elif reply_message["message_type"] == "voice":

        reply_preview = "🎙 Voice message"

    # -----------------------------------------
    # Normal message preview
    # -----------------------------------------

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
    #
    # Delete-for-me messages are hidden only
    # from the user who deleted them.
    #
    # Delete-for-everyone messages remain in
    # the result so they can display the
    # deleted placeholder.
    # -----------------------------------------

    messages = db.execute("""
        SELECT *

        FROM messages

        WHERE

            deleted_for_everyone = 1

            OR

            (
                sender_id = ?

                AND

                receiver_id = ?

                AND

                deleted_for_sender = 0
            )

            OR

            (
                sender_id = ?

                AND

                receiver_id = ?

                AND

                deleted_for_receiver = 0
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

    except (
        TypeError,
        ValueError
    ):

        return

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

        print(
            "❌ Unauthenticated socket tried to send a message."
        )

        return

    sender_id = current_user.id

    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    try:

        receiver_id = int(
            data.get("receiver_id")
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "❌ Invalid receiver ID:",
            data.get("receiver_id")
        )

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
    # Prevent self-message
    # -----------------------------------------

    if sender_id == receiver_id:

        print(
            "❌ User cannot message themselves."
        )

        return

    # -----------------------------------------
    # Reply
    # -----------------------------------------

    reply_to_id = data.get(
        "reply_to_id"
    )

    db = get_db()

    try:

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

            print(
                "❌ Receiver does not exist:",
                receiver_id
            )

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

        cursor = db.execute(
            """
            INSERT INTO messages
            (
                sender_id,
                receiver_id,
                message,
                message_type,
                status,
                reply_to_id,
                deleted_for_sender,
                deleted_for_receiver,
                deleted_for_everyone,
                edited,
                edited_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                'text',
                'sent',
                ?,
                0,
                0,
                0,
                0,
                NULL
            )
            """,
            (
                sender_id,
                receiver_id,
                message,
                reply_to_id
            )
        )

        message_id = cursor.lastrowid

        db.commit()

        print(
            "✅ Message saved:",
            message_id,
            "from",
            sender_id,
            "to",
            receiver_id
        )

    except Exception as e:

        db.rollback()

        print(
            "❌ SEND MESSAGE DATABASE ERROR:",
            e
        )

        return

    finally:

        db.close()

    # -----------------------------------------
    # Sender name
    # -----------------------------------------

    db = get_db()

    sender = db.execute(
        """
        SELECT username
        FROM users
        WHERE id = ?
        """,
        (
            sender_id,
        )
    ).fetchone()

    db.close()

    sender_name = (
        sender["username"]
        if sender
        else "User"
    )

    # -----------------------------------------
    # Message data
    # -----------------------------------------

    message_data = {

        "id":
            message_id,

        "sender_id":
            sender_id,

        "receiver_id":
            receiver_id,

        "sender_name":
            sender_name,

        "message":
            message,

        "message_type":
            "text",

        "status":
            "sent",

        "reply_to_id":
            reply_to_id,

        "reply_preview":
            reply_preview,

        "reply_sender_name":
            reply_sender_name,

        "deleted_for_everyone":
            0,

        "edited":
            0,

        "edited_at":
            None
    }

    # -----------------------------------------
    # Sender
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{sender_id}"
    )

    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{receiver_id}"
    )

    # -----------------------------------------
    # Notification
    # -----------------------------------------

    create_notification(
        receiver_id,
        sender_id,
        message
    )

    print(
        "🔔 Notification created for:",
        receiver_id
    )


# =========================================================
# SEND VOICE MESSAGE
# =========================================================

@socketio.on("send_voice")
def send_voice(data):

    if not current_user.is_authenticated:

        print(
            "❌ Unauthenticated socket tried to send voice."
        )

        return

    sender_id = current_user.id

    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    try:

        receiver_id = int(
            data.get("receiver_id")
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "❌ Invalid voice receiver:",
            data.get("receiver_id")
        )

        return

    if sender_id == receiver_id:

        return

    # -----------------------------------------
    # Audio
    # -----------------------------------------

    audio_data = data.get(
        "audio"
    )

    if not audio_data:

        print(
            "❌ No audio data received."
        )

        return

    # -----------------------------------------
    # Reply
    # -----------------------------------------

    reply_to_id = data.get(
        "reply_to_id"
    )

    # -----------------------------------------
    # Verify receiver + reply
    # -----------------------------------------

    db = get_db()

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

        print(
            "❌ Voice receiver does not exist:",
            receiver_id
        )

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
    # Decode audio
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
            "❌ Voice decode error:",
            e
        )

        return

    # -----------------------------------------
    # File name
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
    # Save audio
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
            "❌ Voice save error:",
            e
        )

        return

    # -----------------------------------------
    # Save message
    # -----------------------------------------

    db = get_db()

    try:

        cursor = db.execute(
            """
            INSERT INTO messages
            (
                sender_id,
                receiver_id,
                message,
                message_type,
                status,
                reply_to_id,
                deleted_for_sender,
                deleted_for_receiver,
                deleted_for_everyone,
                edited,
                edited_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                'voice',
                'sent',
                ?,
                0,
                0,
                0,
                0,
                NULL
            )
            """,
            (
                sender_id,
                receiver_id,
                filename,
                reply_to_id
            )
        )

        message_id = cursor.lastrowid

        db.commit()

    except Exception as e:

        db.rollback()

        print(
            "❌ Voice database error:",
            e
        )

        db.close()

        return

    db.close()

    # -----------------------------------------
    # Audio URL
    # -----------------------------------------

    audio_url = url_for(
        "static",
        filename=f"uploads/voices/{filename}"
    )

    # -----------------------------------------
    # Sender name
    # -----------------------------------------

    db = get_db()

    sender = db.execute(
        """
        SELECT username
        FROM users
        WHERE id = ?
        """,
        (
            sender_id,
        )
    ).fetchone()

    db.close()

    sender_name = (
        sender["username"]
        if sender
        else "User"
    )

    # -----------------------------------------
    # Message data
    # -----------------------------------------

    message_data = {

        "id":
            message_id,

        "sender_id":
            sender_id,

        "receiver_id":
            receiver_id,

        "sender_name":
            sender_name,

        "message":
            filename,

        "audio":
            audio_url,

        "message_type":
            "voice",

        "status":
            "sent",

        "reply_to_id":
            reply_to_id,

        "reply_preview":
            reply_preview,

        "reply_sender_name":
            reply_sender_name,

        "deleted_for_everyone":
            0,

        "edited":
            0,

        "edited_at":
            None
    }

    # -----------------------------------------
    # Sender
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{sender_id}"
    )

    # -----------------------------------------
    # Receiver
    # -----------------------------------------

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{receiver_id}"
    )

    print(
        "🎙 Voice message delivered:",
        sender_id,
        "→",
        receiver_id
    )

    # -----------------------------------------
    # Notification
    # -----------------------------------------

    create_notification(
        receiver_id,
        sender_id,
        "🎙 Voice message"
    )


# =========================================================
# DELETE MESSAGE
# =========================================================

@socketio.on("delete_message")
def delete_message(data):

    if not current_user.is_authenticated:

        print(
            "❌ Unauthenticated user tried to delete a message."
        )

        return

    # -----------------------------------------
    # Message ID
    # -----------------------------------------

    try:

        message_id = int(
            data.get("message_id")
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "❌ Invalid message ID:",
            data.get("message_id")
        )

        return

    # -----------------------------------------
    # Delete type
    # -----------------------------------------

    delete_type = str(
        data.get(
            "delete_type",
            ""
        )
    ).strip().lower()

    if delete_type not in (
        "me",
        "everyone"
    ):

        print(
            "❌ Invalid delete type:",
            delete_type
        )

        return

    db = get_db()

    try:

        # -----------------------------------------
        # Find message
        # -----------------------------------------

        message = db.execute(
            """
            SELECT *

            FROM messages

            WHERE id = ?
            """,
            (
                message_id,
            )
        ).fetchone()

        if not message:

            print(
                "❌ Message not found:",
                message_id
            )

            return

        sender_id = message["sender_id"]

        receiver_id = message["receiver_id"]

        # -----------------------------------------
        # Verify user belongs to conversation
        # -----------------------------------------

        if current_user.id not in (
            sender_id,
            receiver_id
        ):

            print(
                "❌ Unauthorized message deletion attempt."
            )

            return

        # =================================================
        # DELETE FOR ME
        # =================================================

        if delete_type == "me":

            if current_user.id == sender_id:

                db.execute(
                    """
                    UPDATE messages

                    SET deleted_for_sender = 1

                    WHERE id = ?
                    """,
                    (
                        message_id,
                    )
                )

            else:

                db.execute(
                    """
                    UPDATE messages

                    SET deleted_for_receiver = 1

                    WHERE id = ?
                    """,
                    (
                        message_id,
                    )
                )

            db.commit()

            # -----------------------------------------
            # Tell current user's browser
            # -----------------------------------------

            socketio.emit(
                "message_deleted_for_me",
                {
                    "message_id":
                        message_id
                },
                room=f"user_{current_user.id}"
            )

            print(
                "🗑 Message deleted for user:",
                current_user.id,
                "message:",
                message_id
            )

            return

        # =================================================
        # DELETE FOR EVERYONE
        # =================================================

        # Only the original sender may use
        # Delete for Everyone.

        if current_user.id != sender_id:

            print(
                "❌ Receiver cannot delete message for everyone."
            )

            return

        db.execute(
            """
            UPDATE messages

            SET
                deleted_for_everyone = 1,
                message = 'This message was deleted'

            WHERE id = ?
            """,
            (
                message_id,
            )
        )

        db.commit()

        deleted_data = {

            "message_id":
                message_id,

            "sender_id":
                sender_id,

            "receiver_id":
                receiver_id,

            "message":
                "This message was deleted",

            "message_type":
                message["message_type"],

            "deleted_for_everyone":
                1
        }

        # -----------------------------------------
        # Sender
        # -----------------------------------------

        socketio.emit(
            "message_deleted_for_everyone",
            deleted_data,
            room=f"user_{sender_id}"
        )

        # -----------------------------------------
        # Receiver
        # -----------------------------------------

        socketio.emit(
            "message_deleted_for_everyone",
            deleted_data,
            room=f"user_{receiver_id}"
        )

        print(
            "🗑 Message deleted for everyone:",
            message_id
        )

    except Exception as e:

        db.rollback()

        print(
            "❌ DELETE MESSAGE ERROR:",
            e
        )

    finally:

        db.close()


## =========================================================
# PHASE 2.3 — EDIT MESSAGE
# =========================================================

@socketio.on("edit_message")
def edit_message(data):

    # -----------------------------------------
    # Check authentication
    # -----------------------------------------

    if not current_user.is_authenticated:

        print(
            "❌ Unauthenticated user tried to edit a message."
        )

        return

    # -----------------------------------------
    # Validate incoming data
    # -----------------------------------------

    if not data:

        print(
            "❌ No edit data received."
        )

        return

    # -----------------------------------------
    # Message ID
    # -----------------------------------------

    try:

        message_id = int(
            data.get("message_id")
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "❌ Invalid edit message ID:",
            data.get("message_id")
        )

        return

    # -----------------------------------------
    # New message
    # -----------------------------------------

    new_message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not new_message:

        print(
            "❌ Edited message cannot be empty."
        )

        return

    # -----------------------------------------
    # Message length
    # -----------------------------------------

    if len(new_message) > 5000:

        print(
            "❌ Edited message is too long."
        )

        return

    db = get_db()

    try:

        # -----------------------------------------
        # Find message
        # -----------------------------------------

        message = db.execute(
            """
            SELECT
                id,
                sender_id,
                receiver_id,
                message,
                message_type,
                deleted_for_everyone
            FROM messages
            WHERE id = ?
            """,
            (
                message_id,
            )
        ).fetchone()

        if not message:

            print(
                "❌ Message not found:",
                message_id
            )

            return

        # -----------------------------------------
        # Basic message information
        # -----------------------------------------

        sender_id = message["sender_id"]

        receiver_id = message["receiver_id"]

        # -----------------------------------------
        # Only sender can edit
        # -----------------------------------------

        if current_user.id != sender_id:

            print(
                "❌ User is not allowed to edit this message."
            )

            return

        # -----------------------------------------
        # Only text messages
        # -----------------------------------------

        if message["message_type"] != "text":

            print(
                "❌ Only text messages can be edited."
            )

            return

        # -----------------------------------------
        # Deleted-for-everyone messages
        # cannot be edited
        # -----------------------------------------

        if message["deleted_for_everyone"]:

            print(
                "❌ Deleted message cannot be edited."
            )

            return

        # -----------------------------------------
        # Save edit time
        # -----------------------------------------

        edited_at = datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # -----------------------------------------
        # Update database
        # -----------------------------------------

        db.execute(
            """
            UPDATE messages

            SET
                message = ?,
                edited = 1,
                edited_at = ?

            WHERE id = ?
            """,
            (
                new_message,
                edited_at,
                message_id
            )
        )

        db.commit()

        # -----------------------------------------
        # Data sent to both users
        # -----------------------------------------

        edited_data = {

            "id":
                message_id,

            "message_id":
                message_id,

            "sender_id":
                sender_id,

            "receiver_id":
                receiver_id,

            "message":
                new_message,

            "text":
                new_message,

            "message_type":
                "text",

            "edited":
                1,

            "edited_at":
                edited_at,

            "deleted_for_everyone":
                0
        }

        # -----------------------------------------
        # Send to sender
        # -----------------------------------------

        socketio.emit(
            "message_edited",
            edited_data,
            room=f"user_{sender_id}"
        )

        # -----------------------------------------
        # Send to receiver
        # -----------------------------------------

        socketio.emit(
            "message_edited",
            edited_data,
            room=f"user_{receiver_id}"
        )

        print(
            "✏️ Message edited successfully:",
            message_id
        )

    except Exception as e:

        db.rollback()

        print(
            "❌ EDIT MESSAGE ERROR:",
            e
        )

    finally:

        db.close()

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
