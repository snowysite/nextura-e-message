import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()

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

from datetime import datetime, timedelta

import sqlite3
import psycopg
from psycopg.rows import dict_row
import os
import base64
import secrets

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

# =========================================================
# DATABASE
# =========================================================

def get_db():

    database_url = os.getenv("DATABASE_URL")

    if database_url:

        conn = psycopg.connect(
            database_url,
            row_factory=dict_row
        )

        return conn

    conn = sqlite3.connect(
        "database.db",
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def db_execute(
    db,
    query,
    params=()
):

    """
    Execute SQL using the correct placeholder
    format for the active database.

    SQLite uses:
        ?

    PostgreSQL uses:
        %s
    """

    if os.getenv("DATABASE_URL"):

        query = query.replace(
            "?",
            "%s"
        )

    return db.execute(
        query,
        params
    )
# def init_db():

    # db = get_db()

    # # -------------------------
    # # USERS
    # # -------------------------

    # db.execute("""
    #     CREATE TABLE IF NOT EXISTS users (

    #         id INTEGER PRIMARY KEY AUTOINCREMENT,

    #         username TEXT UNIQUE NOT NULL,

    #         email TEXT UNIQUE NOT NULL,

    #         password TEXT NOT NULL,

    #         profile_image TEXT
    #             DEFAULT 'default.png'
    #     )
    # """)

    # # -------------------------
    # # MESSAGES
    # # -------------------------

    # db.execute("""
    #     CREATE TABLE IF NOT EXISTS messages (

    #         id INTEGER PRIMARY KEY AUTOINCREMENT,

    #         sender_id INTEGER NOT NULL,

    #         receiver_id INTEGER NOT NULL,

    #         message TEXT NOT NULL,

    #         message_type TEXT
    #             DEFAULT 'text',

    #         timestamp DATETIME
    #             DEFAULT CURRENT_TIMESTAMP,

    #         status TEXT
    #             DEFAULT 'sent'
    #     )
    # """)

    # # -------------------------
    # # NOTIFICATIONS
    # # -------------------------

    # db.execute("""
    #     CREATE TABLE IF NOT EXISTS notifications (

    #         id INTEGER PRIMARY KEY AUTOINCREMENT,

    #         user_id INTEGER NOT NULL,

    #         sender_id INTEGER NOT NULL,

    #         message TEXT,

    #         is_read INTEGER
    #             DEFAULT 0,

    #         created_at DATETIME
    #             DEFAULT CURRENT_TIMESTAMP
    #     )
    # """)

    # # =====================================================
    # # MESSAGE MIGRATIONS
    # # =====================================================

    # message_columns = db.execute(
    #     "PRAGMA table_info(messages)"
    # ).fetchall()

    # message_column_names = [
    #     column["name"]
    #     for column in message_columns
    # ]

    # # -----------------------------------------------------
    # # REPLY TO ID
    # # -----------------------------------------------------

    # if "reply_to_id" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN reply_to_id INTEGER
    #     """)

    #     print(
    #         "✅ Added reply_to_id column to messages table."
    #     )

    #     message_column_names.append(
    #         "reply_to_id"
    #     )

    # # -----------------------------------------------------
    # # DELETE FOR SENDER
    # # -----------------------------------------------------

    # if "deleted_for_sender" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN deleted_for_sender INTEGER
    #         DEFAULT 0
    #     """)

    #     print(
    #         "✅ Added deleted_for_sender column."
    #     )

    #     message_column_names.append(
    #         "deleted_for_sender"
    #     )

    # # -----------------------------------------------------
    # # DELETE FOR RECEIVER
    # # -----------------------------------------------------

    # if "deleted_for_receiver" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN deleted_for_receiver INTEGER
    #         DEFAULT 0
    #     """)

    #     print(
    #         "✅ Added deleted_for_receiver column."
    #     )

    #     message_column_names.append(
    #         "deleted_for_receiver"
    #     )

    # # -----------------------------------------------------
    # # DELETE FOR EVERYONE
    # # -----------------------------------------------------

    # if "deleted_for_everyone" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN deleted_for_everyone INTEGER
    #         DEFAULT 0
    #     """)

    #     print(
    #         "✅ Added deleted_for_everyone column."
    #     )

    #     message_column_names.append(
    #         "deleted_for_everyone"
    #     )

    # # -----------------------------------------------------
    # # PHASE 2.3 — EDITED
    # # -----------------------------------------------------

    # if "edited" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN edited INTEGER
    #         DEFAULT 0
    #     """)

    #     print(
    #         "✅ Added edited column."
    #     )

    #     message_column_names.append(
    #         "edited"
    #     )

    # # -----------------------------------------------------
    # # PHASE 2.3 — EDITED AT
    # # -----------------------------------------------------

    # if "edited_at" not in message_column_names:

    #     db.execute("""
    #         ALTER TABLE messages
    #         ADD COLUMN edited_at DATETIME
    #     """)

    #     print(
    #         "✅ Added edited_at column."
    #     )

    #     message_column_names.append(
    #         "edited_at"
    #     )

    # # =====================================================
    # # PASSWORD RESET MIGRATIONS
    # # =====================================================

    # user_columns = db.execute(
    #     "PRAGMA table_info(users)"
    # ).fetchall()

    # user_column_names = [
    #     column["name"]
    #     for column in user_columns
    # ]

    # # -----------------------------------------------------
    # # PASSWORD RESET TOKEN
    # # -----------------------------------------------------

    # if "reset_token" not in user_column_names:

    #     db.execute("""
    #         ALTER TABLE users
    #         ADD COLUMN reset_token TEXT
    #     """)

    #     print(
    #         "✅ Added reset_token column."
    #     )

    #     user_column_names.append(
    #         "reset_token"
    #     )

    # # -----------------------------------------------------
    # # PASSWORD RESET TOKEN EXPIRY
    # # -----------------------------------------------------

    # if "reset_token_expires" not in user_column_names:

    #     db.execute("""
    #         ALTER TABLE users
    #         ADD COLUMN reset_token_expires DATETIME
    #     """)

    #     print(
    #         "✅ Added reset_token_expires column."
    #     )

    #     user_column_names.append(
    #         "reset_token_expires"
    #     )

    # db.commit()

    # db.close()
def init_db():

    db = get_db()

    database_url = os.getenv("DATABASE_URL")

    # =====================================================
    # POSTGRESQL
    # =====================================================

    if database_url:

        # -------------------------------------------------
        # USERS
        # -------------------------------------------------

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER GENERATED BY DEFAULT AS IDENTITY
                    PRIMARY KEY,

                username TEXT UNIQUE NOT NULL,

                email TEXT UNIQUE NOT NULL,

                password TEXT NOT NULL,

                profile_image TEXT
                    DEFAULT 'default.png',

                reset_token TEXT,

                reset_token_expires TIMESTAMP
            )
        """)

        # -------------------------------------------------
        # MESSAGES
        # -------------------------------------------------

        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (

                id INTEGER GENERATED BY DEFAULT AS IDENTITY
                    PRIMARY KEY,

                sender_id INTEGER NOT NULL,

                receiver_id INTEGER NOT NULL,

                message TEXT NOT NULL,

                message_type TEXT
                    DEFAULT 'text',

                timestamp TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                status TEXT
                    DEFAULT 'sent',

                reply_to_id INTEGER,

                deleted_for_sender INTEGER
                    DEFAULT 0,

                deleted_for_receiver INTEGER
                    DEFAULT 0,

                deleted_for_everyone INTEGER
                    DEFAULT 0,

                edited INTEGER
                    DEFAULT 0,

                edited_at TIMESTAMP
            )
        """)

        # -------------------------------------------------
        # NOTIFICATIONS
        # -------------------------------------------------

        db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (

                id INTEGER GENERATED BY DEFAULT AS IDENTITY
                    PRIMARY KEY,

                user_id INTEGER NOT NULL,

                sender_id INTEGER NOT NULL,

                message TEXT,

                is_read INTEGER
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------------------------------------------------
        # SAFETY MIGRATIONS
        # -------------------------------------------------

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS reply_to_id INTEGER
        """)

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS deleted_for_sender INTEGER
            DEFAULT 0
        """)

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS deleted_for_receiver INTEGER
            DEFAULT 0
        """)

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS deleted_for_everyone INTEGER
            DEFAULT 0
        """)

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS edited INTEGER
            DEFAULT 0
        """)

        db.execute("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP
        """)

        db.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token TEXT
        """)

        db.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP
        """)

        print("✅ PostgreSQL database initialized.")

    # =====================================================
    # SQLITE
    # =====================================================

    else:

        # -------------------------------------------------
        # USERS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # MESSAGES
        # -------------------------------------------------

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

        # -------------------------------------------------
        # NOTIFICATIONS
        # -------------------------------------------------

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

        # =================================================
        # MESSAGE MIGRATIONS
        # =================================================

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

            print("✅ Added reply_to_id column to messages table.")

        if "deleted_for_sender" not in message_column_names:

            db.execute("""
                ALTER TABLE messages
                ADD COLUMN deleted_for_sender INTEGER
                DEFAULT 0
            """)

            print("✅ Added deleted_for_sender column.")

        if "deleted_for_receiver" not in message_column_names:

            db.execute("""
                ALTER TABLE messages
                ADD COLUMN deleted_for_receiver INTEGER
                DEFAULT 0
            """)

            print("✅ Added deleted_for_receiver column.")

        if "deleted_for_everyone" not in message_column_names:

            db.execute("""
                ALTER TABLE messages
                ADD COLUMN deleted_for_everyone INTEGER
                DEFAULT 0
            """)

            print("✅ Added deleted_for_everyone column.")

        if "edited" not in message_column_names:

            db.execute("""
                ALTER TABLE messages
                ADD COLUMN edited INTEGER
                DEFAULT 0
            """)

            print("✅ Added edited column.")

        if "edited_at" not in message_column_names:

            db.execute("""
                ALTER TABLE messages
                ADD COLUMN edited_at DATETIME
            """)

            print("✅ Added edited_at column.")

        # =================================================
        # PASSWORD RESET MIGRATIONS
        # =================================================

        user_columns = db.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        user_column_names = [
            column["name"]
            for column in user_columns
        ]

        if "reset_token" not in user_column_names:

            db.execute("""
                ALTER TABLE users
                ADD COLUMN reset_token TEXT
            """)

            print("✅ Added reset_token column.")

        if "reset_token_expires" not in user_column_names:

            db.execute("""
                ALTER TABLE users
                ADD COLUMN reset_token_expires DATETIME
            """)

            print("✅ Added reset_token_expires column.")

        print("✅ SQLite database initialized.")

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

    # -----------------------------------------
    # Find original message
    # -----------------------------------------

    reply_message = db_execute(
        db,
        """
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

        """,
        (
            reply_to_id,

            sender_id,
            receiver_id,

            receiver_id,
            sender_id
        )
    ).fetchone()

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

    if os.getenv("DATABASE_URL"):

        cursor = db_execute(
            db,
            """
            INSERT INTO notifications
            (
                user_id,
                sender_id,
                message
            )
            VALUES (?, ?, ?)
            RETURNING id
            """,
            (
                receiver_id,
                sender_id,
                message
            )
        )

        notification_id = cursor.fetchone()["id"]

    else:

        cursor = db_execute(
            db,
            """
            INSERT INTO notifications
            (
                user_id,
                sender_id,
                message
            )
            VALUES (?, ?, ?)
            """,
            (
                receiver_id,
                sender_id,
                message
            )
        )

        notification_id = cursor.lastrowid

    sender = db_execute(
        db,
        """
        SELECT username
        FROM users
        WHERE id = ?
        """,
        (
            sender_id,
        )
    ).fetchone()

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
#         # =========================================================
# # CREATE NOTIFICATION
# # =========================================================

# def create_notification(
#     receiver_id,
#     sender_id,
#     message
# ):

#     """
#     Creates a notification in the database
#     and immediately sends it to the receiver
#     through Socket.IO.
#     """

#     db = get_db()

#     if os.getenv("DATABASE_URL"):

#         cursor = db_execute(
#             db,
#             """
#             INSERT INTO notifications
#             (
#                 user_id,
#                 sender_id,
#                 message
#             )
#             VALUES (?, ?, ?)
#             RETURNING id
#             """,
#             (
#                 receiver_id,
#                 sender_id,
#                 message
#             )
#         )

#         notification_id = cursor.fetchone()["id"]

#     else:

#         cursor = db_execute(
#             db,
#             """
#             INSERT INTO notifications
#             (
#                 user_id,
#                 sender_id,
#                 message
#             )
#             VALUES (?, ?, ?)
#             """,
#             (
#                 receiver_id,
#                 sender_id,
#                 message
#             )
#         )

#         notification_id = cursor.lastrowid

#     sender = db_execute(
#         db,
#         """
#         SELECT username
#         FROM users
#         WHERE id = ?
#         """,
#         (
#             sender_id,
#         )
#     ).fetchone()

#     sender_name = (
#         sender["username"]
#         if sender
#         else "Someone"
#     )

#     db.commit()

#     db.close()

#     socketio.emit(
#         "new_notification",
#         {
#             "id": notification_id,

#             "sender_id": sender_id,

#             "sender_name": sender_name,

#             "receiver_id": receiver_id,

#             "message": message
#         },

#         room=f"user_{receiver_id}"
#     )


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

    user = db_execute(
        db,
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

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if (
            not username
            or not email
            or not password
            or not confirm_password
        ):

            flash(
                "Please complete all registration fields."
            )

            return render_template(
                "signup.html"
            )

        # -------------------------------------------------
        # USERNAME VALIDATION
        # -------------------------------------------------

        if len(username) < 3 or len(username) > 30:

            flash(
                "Username must be between 3 and 30 characters."
            )

            return render_template(
                "signup.html"
            )

        if not re.fullmatch(
            r"[A-Za-z0-9_]+",
            username
        ):

            flash(
                "Username can only contain letters, numbers, and underscores."
            )

            return render_template(
                "signup.html"
            )

        # -------------------------------------------------
        # EMAIL VALIDATION
        # -------------------------------------------------

        if not re.fullmatch(
            r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
            email
        ):

            flash(
                "Please enter a valid email address."
            )

            return render_template(
                "signup.html"
            )
        # -------------------------------------------------
        # PASSWORD VALIDATION
        # -------------------------------------------------

        if len(password) < 8:

            flash(
                "Password must be at least 8 characters long."
            )

            return render_template(
                "signup.html"
            )

        if not re.search(
            r"[A-Z]",
            password
        ):

            flash(
                "Password must contain at least one uppercase letter."
            )

            return render_template(
                "signup.html"
            )

        if not re.search(
            r"[a-z]",
            password
        ):

            flash(
                "Password must contain at least one lowercase letter."
            )

            return render_template(
                "signup.html"
            )

        if not re.search(
            r"[0-9]",
            password
        ):

            flash(
                "Password must contain at least one number."
            )

            return render_template(
                "signup.html"
            )

        if not re.search(
            r"[^A-Za-z0-9]",
            password
        ):

            flash(
                "Password must contain at least one special character."
            )

            return render_template(
                "signup.html"
            )

       # -------------------------------------------------
# CONFIRM PASSWORD
# -------------------------------------------------

        if password != confirm_password:

            flash(
                "Passwords do not match."
            )

            return render_template(
                "signup.html"
            )

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        db = get_db()

        try:

            # -------------------------------------------------
            # CHECK FOR EXISTING ACCOUNT
            # -------------------------------------------------

            existing_user = db_execute(
                db,
                """
                SELECT id
                FROM users
                WHERE username = ?
                   OR email = ?
                LIMIT 1
                """,
                (
                    username,
                    email
                )
            ).fetchone()

            if existing_user:

                flash(
                    "Username or email already exists."
                )

                return render_template(
                    "signup.html"
                )

            # -------------------------------------------------
            # CREATE ACCOUNT
            #
            # Password is NEVER stored directly.
            # generate_password_hash() creates the secure
            # password hash stored in the database.
            # -------------------------------------------------

            password_hash = generate_password_hash(
                password
            )

            db_execute(
                db,
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
                    password_hash
                )
            )

            db.commit()

            flash(
                "Account created successfully. Please login."
            )

            return redirect(
                url_for("login")
            )

        except (
            sqlite3.IntegrityError,
            psycopg.IntegrityError
        ):

            db.rollback()

            flash(
                "Username or email already exists."
            )

            return render_template(
                "signup.html"
            )

        except Exception as e:

            db.rollback()

            print(
                "❌ SIGNUP DATABASE ERROR:",
                e
            )

            flash(
                "An unexpected database error occurred. Please try again."
            )

            return render_template(
                "signup.html"
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

        user = db_execute(
            db,
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

def send_password_reset_email(recipient_email, reset_link):
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", mail_username)

    if not mail_username or not mail_password:
        raise RuntimeError("Email configuration is missing from .env")

    msg = EmailMessage()
    msg["Subject"] = "Reset your Nextura-E-Message password"
    msg["From"] = mail_from
    msg["To"] = recipient_email

    msg.set_content(
        f"""Hello,

We received a request to reset your Nextura-E-Message password.

Click the link below to create a new password:

{reset_link}

This link will expire in 30 minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
Nextura-E-Message
"""
    )

    with smtplib.SMTP(mail_server, mail_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(mail_username, mail_password)
        server.send_message(msg)

# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        # Always show the same message so users
        # cannot discover which emails are registered.
        generic_message = (
            "If an account exists for that email, "
            "a password reset link has been sent."
        )

        if not email:

            flash(generic_message)

            return redirect(
                url_for("forgot_password")
            )
        db = get_db()

        try:

            user = db_execute(
                db,
                """
                SELECT id, email
                FROM users
                WHERE LOWER(email) = ?
                """,
                (
                    email,
                )
            ).fetchone()

            if user:

                reset_token = secrets.token_urlsafe(48)

                expires_at = (
                    datetime.utcnow()
                    + timedelta(minutes=30)
                ).isoformat()

                db_execute(
                    db,
                    """
                    UPDATE users
                    SET reset_token = ?,
                        reset_token_expires = ?
                    WHERE id = ?
                    """,
                    (
                        reset_token,
                        expires_at,
                        user["id"]
                    )
                )

                db.commit()

                # Create the password reset link.
                reset_link = url_for(
                    "reset_password",
                    token=reset_token,
                    _external=True
                )
                # Send the reset link by email.
                try:
                    send_password_reset_email(
                        user["email"],
                        reset_link
                    )

                except Exception as email_error:
                    print(
                        "Password reset email error:",
                        email_error
                    )

        except Exception as e:

            db.rollback()

            print(
                "Forgot password error:",
                e
            )

        finally:

            db.close()

        flash(generic_message)

        return redirect(
            url_for("forgot_password")
        )

    return render_template(
        "forgot_password.html"
    )


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    db = get_db()

    try:

        user = db_execute(
            db,
            """
            SELECT id, email, reset_token,
                   reset_token_expires
            FROM users
            WHERE reset_token = ?
            """,
            (
                token,
            )
        ).fetchone()

        # -----------------------------------------
        # Invalid or already-used token
        # -----------------------------------------

        if not user:

            flash(
                "This password reset link is invalid or has already been used."
            )

            return redirect(
                url_for("login")
            )

        # -----------------------------------------
        # Check expiration
        # -----------------------------------------

        expires_value = user["reset_token_expires"]

        try:

            if isinstance(
                expires_value,
                datetime
            ):

                expires_at = expires_value

            else:

                expires_at = datetime.fromisoformat(
                    str(expires_value)
                )

        except (
            TypeError,
            ValueError
        ):

            flash(
                "This password reset link is invalid or has expired."
            )

            return redirect(
                url_for("login")
            )

        # -----------------------------------------
        # Expired token
        # -----------------------------------------

        if datetime.utcnow() > expires_at:

            db_execute(
                db,
                """
                UPDATE users
                SET reset_token = NULL,
                    reset_token_expires = NULL
                WHERE id = ?
                """,
                (
                    user["id"],
                )
            )

            db.commit()

            flash(
                "This password reset link has expired. Please request a new one."
            )

            return redirect(
                url_for("forgot_password")
            )

        # -----------------------------------------
        # POST - Set new password
        # -----------------------------------------

        if request.method == "POST":

            password = request.form.get(
                "password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

            # -----------------------------------------
            # Password length
            # -----------------------------------------

            if len(password) < 8:

                flash(
                    "Password must be at least 8 characters."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Uppercase
            # -----------------------------------------

            if not re.search(
                r"[A-Z]",
                password
            ):

                flash(
                    "Password must contain at least one uppercase letter."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Lowercase
            # -----------------------------------------

            if not re.search(
                r"[a-z]",
                password
            ):

                flash(
                    "Password must contain at least one lowercase letter."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Number
            # -----------------------------------------

            if not re.search(
                r"\d",
                password
            ):

                flash(
                    "Password must contain at least one number."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Special character
            # -----------------------------------------

            if not re.search(
                r"[^A-Za-z0-9]",
                password
            ):

                flash(
                    "Password must contain at least one special character."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Confirm password
            # -----------------------------------------

            if password != confirm_password:

                flash(
                    "Passwords do not match."
                )

                return render_template(
                    "reset_password.html",
                    token=token
                )

            # -----------------------------------------
            # Hash new password
            # -----------------------------------------

            password_hash = generate_password_hash(
                password
            )

            # -----------------------------------------
            # Update password
            # -----------------------------------------

            db_execute(
                db,
                """
                UPDATE users
                SET password = ?,
                    reset_token = NULL,
                    reset_token_expires = NULL
                WHERE id = ?
                """,
                (
                    password_hash,
                    user["id"]
                )
            )

            db.commit()

            flash(
                "Your password has been reset successfully. You can now login."
            )

            return redirect(
                url_for("login")
            )

        # -----------------------------------------
        # GET - Show reset form
        # -----------------------------------------

        return render_template(
            "reset_password.html",
            token=token
        )

    except Exception as e:

        db.rollback()

        print(
            "Reset password error:",
            e
        )

        flash(
            "Something went wrong. Please request a new password reset link."
        )

        return redirect(
            url_for("forgot_password")
        )

    finally:

        db.close()

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
# DASHBOARD DATA API
# =========================================================

@app.route("/api/dashboard")
# =========================================================
# DASHBOARD DATA API
# =========================================================

@app.route("/api/dashboard")
@login_required
def dashboard_data():

    db = get_db()

    try:

        # -----------------------------------------
        # Total contacts
        # -----------------------------------------

        contacts = db_execute(
            db,
            """
            SELECT COUNT(*) AS count
            FROM users
            WHERE id != ?
            """,
            (
                current_user.id,
            )
        ).fetchone()["count"]

        # -----------------------------------------
        # People the current user has conversations
        # with
        # -----------------------------------------

        conversations = db_execute(
            db,
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT DISTINCT
                    CASE
                        WHEN sender_id = ?
                        THEN receiver_id
                        ELSE sender_id
                    END AS user_id
                FROM messages
                WHERE
                    sender_id = ?
                    OR receiver_id = ?
            )
            """,
            (
                current_user.id,
                current_user.id,
                current_user.id
            )
        ).fetchone()["count"]

        # -----------------------------------------
        # Unread notifications
        # -----------------------------------------

        unread = db_execute(
            db,
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id = ?
            AND is_read = 0
            """,
            (
                current_user.id,
            )
        ).fetchone()["count"]

        # -----------------------------------------
        # Recent conversations
        #
        # Get the latest message exchanged with
        # each person.
        # -----------------------------------------

        recent = db_execute(
            db,
            """
            SELECT
                other.id AS user_id,
                other.username,
                other.profile_image,
                m.message,
                m.message_type,
                m.timestamp,
                m.sender_id,
                m.status

            FROM messages m

            JOIN users other
            ON other.id =
                CASE
                    WHEN m.sender_id = ?
                    THEN m.receiver_id
                    ELSE m.sender_id
                END

            WHERE
                (
                    m.sender_id = ?
                    OR m.receiver_id = ?
                )

            AND m.id IN (
                SELECT MAX(m2.id)

                FROM messages m2

                WHERE
                    (
                        m2.sender_id = ?
                        AND m2.receiver_id = other.id
                    )

                    OR

                    (
                        m2.sender_id = other.id
                        AND m2.receiver_id = ?
                    )
            )

            ORDER BY m.timestamp DESC

            LIMIT 10
            """,
            (
                current_user.id,

                current_user.id,
                current_user.id,

                current_user.id,
                current_user.id
            )
        ).fetchall()

        recent_conversations = []

        for conversation in recent:

            message_preview = (
                conversation["message"]
                or ""
            )

            if conversation["message_type"] == "voice":

                message_preview = (
                    "🎙 Voice message"
                )

            elif conversation["message_type"] == "image":

                message_preview = (
                    "🖼 Image"
                )

            elif conversation["message_type"] == "file":

                message_preview = (
                    "📎 File"
                )

            if len(message_preview) > 45:

                message_preview = (
                    message_preview[:45]
                    + "..."
                )

            recent_conversations.append({

                "user_id":
                    conversation["user_id"],

                "username":
                    conversation["username"],

                "profile_image":
                    conversation["profile_image"]
                    or "default.png",

                "message":
                    message_preview,

                "timestamp":
                    conversation["timestamp"],

                "sender_id":
                    conversation["sender_id"],

                "status":
                    conversation["status"],

                "online":
                    conversation["user_id"]
                    in online_users
            })

        return jsonify({

            "success": True,

            "stats": {

                "contacts":
                    contacts,

                "conversations":
                    conversations,

                "notifications":
                    unread
            },

            "recent_conversations":
                recent_conversations
        })

    except Exception as e:

        print(
            "❌ DASHBOARD API ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error":
                "Unable to load dashboard data."
        }), 500

    finally:

        db.close()


# =========================================================
# USERS
# =========================================================

@app.route("/users")
@login_required
def users():

    db = get_db()

    try:

        users = db_execute(
            db,
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

        return render_template(
            "users.html",

            users=users,

            online_users=online_users
        )

    finally:

        db.close()

# =========================================================
# NOTIFICATION API
# =========================================================

@app.route("/api/notifications")
@login_required
def get_notifications():

    db = get_db()

    try:

        notifications = db_execute(
            db,
            """
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

            """,
            (
                current_user.id,
            )
        ).fetchall()

        # -----------------------------------------
        # Unread notification count
        # -----------------------------------------

        unread = db_execute(
            db,
            """
            SELECT COUNT(*) AS count

            FROM notifications

            WHERE user_id = ?

            AND is_read = 0

            """,
            (
                current_user.id,
            )
        ).fetchone()["count"]

        return jsonify({

            "success": True,

            "unread_count":
                unread,

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

    except Exception as e:

        print(
            "❌ NOTIFICATION API ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error":
                "Unable to load notifications."
        }), 500

    finally:

        db.close()


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

    try:
        db_execute(
            db,
            """
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ?
            """,
            (
                current_user.id,
            )
        )

        db.commit()

        return jsonify({
            "success": True,
            "message": "Notifications marked as read."
        })

    except Exception as e:
        db.rollback()
        print("❌ MARK NOTIFICATIONS READ ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Failed to mark notifications as read."
        }), 500

    finally:
        db.close()

# =========================================================
# CHAT PAGE
# =========================================================

@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):

    db = get_db()

    try:
        receiver = db_execute(
            db,
            """
            SELECT id, username, profile_image
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if not receiver:
            flash("User not found.")
            return redirect(url_for("users"))

        messages = db_execute(
            db,
            """
            SELECT *
            FROM messages
            WHERE
                deleted_for_everyone = 1
                OR
                (
                    sender_id = ?
                    AND receiver_id = ?
                    AND deleted_for_sender = 0
                )
                OR
                (
                    sender_id = ?
                    AND receiver_id = ?
                    AND deleted_for_receiver = 0
                )
            ORDER BY timestamp ASC
            """,
            (
                current_user.id,
                user_id,
                user_id,
                current_user.id
            )
        ).fetchall()

        db_execute(
            db,
            """
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ?
            AND sender_id = ?
            """,
            (
                current_user.id,
                user_id
            )
        )

        db.commit()

        return render_template(
            "chat.html",
            receiver=receiver,
            messages=messages,
            my_id=current_user.id
        )

    except Exception as e:
        db.rollback()
        print("❌ CHAT DATABASE ERROR:", e)

        flash("Unable to open chat.")
        return redirect(url_for("users"))

    finally:
        db.close()
    # # -----------------------------------------
    # # Get receiver
    # # -----------------------------------------

    # receiver = db.execute(
    #     """
    #     SELECT

    #         id,

    #         username,

    #         profile_image

    #     FROM users

    #     WHERE id = ?

    #     """,
    #     (
    #         user_id,
    #     )
    # ).fetchone()

    # if not receiver:

    #     db.close()

    #     flash(
    #         "User not found."
    #     )

    #     return redirect(
    #         url_for("users")
    #     )

    # # -----------------------------------------
    # # Get messages
    # #
    # # Delete-for-me messages are hidden only
    # # from the user who deleted them.
    # #
    # # Delete-for-everyone messages remain in
    # # the result so they can display the
    # # deleted placeholder.
    # # -----------------------------------------

    # messages = db.execute("""
    #     SELECT *

    #     FROM messages

    #     WHERE

    #         deleted_for_everyone = 1

    #         OR

    #         (
    #             sender_id = ?

    #             AND

    #             receiver_id = ?

    #             AND

    #             deleted_for_sender = 0
    #         )

    #         OR

    #         (
    #             sender_id = ?

    #             AND

    #             receiver_id = ?

    #             AND

    #             deleted_for_receiver = 0
    #         )

    #     ORDER BY
    #         timestamp ASC

    # """, (
    #     current_user.id,

    #     user_id,

    #     user_id,

    #     current_user.id
    # )).fetchall()

    # # -----------------------------------------
    # # Mark notifications from this user
    # # as read
    # # -----------------------------------------

    # db.execute("""
    #     UPDATE notifications

    #     SET is_read = 1

    #     WHERE user_id = ?

    #     AND sender_id = ?

    # """, (
    #     current_user.id,

    #     user_id
    # ))

    # db.commit()

    # db.close()

    # return render_template(
    #     "chat.html",

    #     receiver=receiver,

    #     messages=messages,

    #     my_id=current_user.id
    # )


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

        receiver = db_execute(
            db,
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

        # -----------------------------------------
        # Save message
        # -----------------------------------------

        if os.getenv("DATABASE_URL"):

            cursor = db_execute(
                db,
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
                RETURNING id
                """,
                (
                    sender_id,
                    receiver_id,
                    message,
                    reply_to_id
                )
            )

            message_id = cursor.fetchone()["id"]

        else:

            cursor = db_execute(
                db,
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

    sender = db_execute(
        db,
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
# MESSAGE DELIVERED
# =========================================================

@socketio.on("message_delivered")
def message_delivered(data):

    if not current_user.is_authenticated:
        return

    try:
        message_id = int(data.get("message_id"))
    except (TypeError, ValueError):
        print(
            "❌ Invalid delivered message ID:",
            data.get("message_id")
        )
        return

    db = get_db()

    try:
        message = db_execute(
            db,
            """
            SELECT
                id,
                sender_id,
                receiver_id,
                status
            FROM messages
            WHERE id = ?
            """,
            (message_id,)
        ).fetchone()

        if not message:
            return

        sender_id = message["sender_id"]
        receiver_id = message["receiver_id"]

        # Only the receiver can confirm delivery.
        if current_user.id != receiver_id:
            print(
                "❌ Unauthorized delivery acknowledgment:",
                current_user.id,
                "message:",
                message_id
            )
            return

        # A seen message is already beyond delivered.
        if message["status"] == "seen":
            return

        db_execute(
            db,
            """
            UPDATE messages
            SET status = 'delivered'
            WHERE id = ?
            AND status = 'sent'
            """,
            (message_id,)
        )

        db.commit()

        socketio.emit(
            "message_status",
            {
                "message_id": message_id,
                "status": "delivered"
            },
            room=f"user_{sender_id}"
        )

        print(
            "📬 Message delivered:",
            message_id,
            "to",
            receiver_id
        )

    except Exception as e:
        db.rollback()
        print(
            "❌ MESSAGE DELIVERED ERROR:",
            e
        )

    finally:
        db.close()

# =========================================================
# MESSAGE SEEN
# =========================================================

@socketio.on("message_seen")
def message_seen(data):

    if not current_user.is_authenticated:
        return

    try:
        message_id = int(data.get("message_id"))
    except (TypeError, ValueError):
        print(
            "❌ Invalid seen message ID:",
            data.get("message_id")
        )
        return

    db = get_db()

    try:
        message = db_execute(
            db,
            """
            SELECT
                id,
                sender_id,
                receiver_id,
                status
            FROM messages
            WHERE id = ?
            """,
            (message_id,)
        ).fetchone()

        if not message:
            return

        sender_id = message["sender_id"]
        receiver_id = message["receiver_id"]

        # Only the receiver can mark the message as seen.
        if current_user.id != receiver_id:
            print(
                "❌ Unauthorized seen acknowledgment:",
                current_user.id,
                "message:",
                message_id
            )
            return

        if message["status"] == "seen":
            return

        db_execute(
            db,
            """
            UPDATE messages
            SET status = 'seen'
            WHERE id = ?
            AND status IN ('sent', 'delivered')
            """,
            (message_id,)
        )

        db.commit()

        socketio.emit(
            "message_status",
            {
                "message_id": message_id,
                "status": "seen"
            },
            room=f"user_{sender_id}"
        )

        print(
            "👀 Message seen:",
            message_id,
            "by",
            receiver_id
        )

    except Exception as e:
        db.rollback()
        print(
            "❌ MESSAGE SEEN ERROR:",
            e
        )

    finally:
        db.close()
# =========================================================
# SEND VOICE MESSAGE
# =========================================================
@socketio.on("send_voice")
def send_voice(data):

    if not current_user.is_authenticated:
        return

    receiver_id = data.get("receiver_id")
    audio_data = data.get("audio")

    try:
        receiver_id = int(receiver_id)
    except (TypeError, ValueError):
        print("❌ Invalid receiver ID:", receiver_id)
        return

    if not audio_data:
        print("❌ No voice audio received.")
        return

    if receiver_id == current_user.id:
        print("❌ Cannot send voice message to yourself.")
        return

    # --------------------------------------------------
    # Verify receiver
    # --------------------------------------------------

    db = get_db()

    try:
        receiver = db_execute(
            db,
            """
            SELECT id, username
            FROM users
            WHERE id = ?
            """,
            (receiver_id,)
        ).fetchone()
    finally:
        db.close()

    if not receiver:
        print("❌ Voice message receiver not found:", receiver_id)
        return

    # --------------------------------------------------
    # Reply information
    # --------------------------------------------------

    reply_to_id = data.get("reply_to_id")

    db = get_db()

    try:
        (
            reply_message_id,
            reply_preview,
            reply_sender_name
        ) = get_reply_info(
            db,
            reply_to_id,
            current_user.id,
            receiver_id
        )
    finally:
        db.close()

    # --------------------------------------------------
    # Decode audio
    # --------------------------------------------------

    try:
        if "," in audio_data:
            audio_data = audio_data.split(",", 1)[1]

        audio_bytes = base64.b64decode(audio_data)

    except Exception as e:
        print("❌ VOICE DECODE ERROR:", e)
        return

    # --------------------------------------------------
    # Save audio file
    # --------------------------------------------------

    filename = (
        f"voice_{current_user.id}_"
        f"{secrets.token_hex(12)}.webm"
    )

    filepath = os.path.join(
        VOICE_FOLDER,
        filename
    )

    try:
        with open(filepath, "wb") as audio_file:
            audio_file.write(audio_bytes)

    except Exception as e:
        print("❌ VOICE FILE SAVE ERROR:", e)
        return

    # URL used by the browser to play the audio.
    audio_url = url_for(
        "static",
        filename=f"uploads/voices/{filename}"
    )

    # --------------------------------------------------
    # Save message in database
    # --------------------------------------------------

    db = get_db()

    try:
        if os.getenv("DATABASE_URL"):

            cursor = db_execute(
                db,
                """
                INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    message,
                    message_type,
                    reply_to_id,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id, timestamp
                """,
                (
                    current_user.id,
                    receiver_id,
                    audio_url,
                    "voice",
                    reply_message_id,
                    "sent"
                )
            )

            new_message = cursor.fetchone()

            message_id = new_message["id"]
            timestamp = new_message["timestamp"]

        else:

            cursor = db_execute(
                db,
                """
                INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    message,
                    message_type,
                    reply_to_id,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    receiver_id,
                    audio_url,
                    "voice",
                    reply_message_id,
                    "sent"
                )
            )

            message_id = cursor.lastrowid

            timestamp = db_execute(
                db,
                """
                SELECT timestamp
                FROM messages
                WHERE id = ?
                """,
                (message_id,)
            ).fetchone()["timestamp"]

        db.commit()

    except Exception as e:

        db.rollback()

        print(
            "❌ VOICE MESSAGE DATABASE ERROR:",
            e
        )

        return

    finally:
        db.close()

    # --------------------------------------------------
    # Sender information
    # --------------------------------------------------

    db = get_db()

    try:
        sender = db_execute(
            db,
            """
            SELECT username, profile_image
            FROM users
            WHERE id = ?
            """,
            (current_user.id,)
        ).fetchone()
    finally:
        db.close()

    sender_name = (
        sender["username"]
        if sender
        else "User"
    )

    sender_profile_image = (
        sender["profile_image"]
        if sender
        else "default.png"
    )

    # --------------------------------------------------
    # Message data sent to both clients
    # --------------------------------------------------

    message_data = {
        "id": message_id,
        "sender_id": current_user.id,
        "receiver_id": receiver_id,
        "message": audio_url,
        "message_type": "voice",
        "timestamp": timestamp.isoformat()
        if hasattr(timestamp, "isoformat")
        else str(timestamp),
        "status": "sent",

        "sender_name": sender_name,
        "sender_profile_image": sender_profile_image,

        "reply_to_id": reply_message_id,
        "reply_preview": reply_preview,
        "reply_sender_name": reply_sender_name
    }

    # --------------------------------------------------
    # Send message to sender and receiver
    # --------------------------------------------------

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{current_user.id}"
    )

    socketio.emit(
        "receive_message",
        message_data,
        room=f"user_{receiver_id}"
    )

    # --------------------------------------------------
    # Create notification
    # --------------------------------------------------

    create_notification(
        receiver_id,
        current_user.id,
        "🎙 Voice message"
    )

    print(
        "🎙 Voice message sent:",
        message_id,
        "from",
        current_user.id,
        "to",
        receiver_id
    )

    audio_url = url_for(
    "static",
    filename=f"uploads/voices/{filename}"
)    # -----------------------------------------
    # Sender name
    # -----------------------------------------

    db = get_db()

    try:
        sender = db_execute(
            db,
            """
            SELECT username
            FROM users
            WHERE id = ?
            """,
            (
                sender_id,
            )
        ).fetchone()
    finally:
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

        message = db_execute(
            db,
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

                db_execute(
                    db,
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

                db_execute(
                    db,
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

        db_execute(
            db,
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


# =========================================================
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

        message = db_execute(
            db,
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

        db_execute(
            db,
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