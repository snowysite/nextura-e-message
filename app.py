from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, join_room, emit
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nextura_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable WebSocket support

online_users = set()

# -------------------- Database --------------------
def get_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
               
        )
               
               
    """)
    db.commit()

    

init_db()

# -------------------- Routes --------------------
@app.route("/")
def home():
    return redirect("/dashboard" if "user_id" in session else "/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            db.commit()
            return redirect("/login")
        except:
            return "Username or Email already exists"
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            return "Invalid login details"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html", username=session["username"])

@app.route("/users")
def users():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    users = db.execute(
        "SELECT id, username FROM users WHERE id != ?",
        (session["user_id"],)
    ).fetchall()
    return render_template("users.html", users=users, online_users=online_users)


@app.route("/chat/<int:user_id>")
def chat(user_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    receiver = db.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    messages = db.execute("""
        SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp
    """, (session["user_id"], user_id, user_id, session["user_id"])).fetchall()
    return render_template(
        "chat.html",
        receiver=receiver,
        messages=messages,
        my_id=session["user_id"]
    )

# -------------------- SocketIO --------------------
def get_room_id(user1, user2):
    """Consistent room ID for two users"""
    user1 = int(user1)
    user2 = int(user2)
    return f"chat_{min(user1,user2)}_{max(user1,user2)}"

@socketio.on('join')
def on_join(data):
    room = get_room_id(data['sender_id'], data['receiver_id'])
    join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = int(data['sender_id'])
    receiver_id = int(data['receiver_id'])
    message = data['message']

    db = get_db()
    cursor = db.execute(
        "INSERT INTO messages (sender_id, receiver_id, message, status) VALUES (?, ?, ?, ?)",
        (sender_id, receiver_id, message, 'delivered')
    )
    db.commit()

    msg_id = cursor.lastrowid
    room = get_room_id(sender_id, receiver_id)

    emit('receive_message', {
        'id': msg_id,
        'sender_id': sender_id,
        'message': message,
        'status': 'delivered'
    }, room=room)

    # Send message to both users in the room
    room = get_room_id(sender_id, receiver_id)
    emit('receive_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }, room=room)

@socketio.on('user_connected')
def handle_user_connected(user_id):
    user_id = int(user_id)
    online_users.add(user_id)
    emit('status_update', list(online_users), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    # remove user from online list
    user_id = session.get('user_id')
    if user_id in online_users:
        online_users.remove(user_id)
    emit('status_update', list(online_users), broadcast=True)

@socketio.on('mark_seen')
def mark_seen(data):
    sender_id = int(data['sender_id'])
    receiver_id = int(data['receiver_id'])

    db = get_db()
    db.execute("""
        UPDATE messages
        SET status = 'seen'
        WHERE sender_id = ? AND receiver_id = ?
    """, (sender_id, receiver_id))
    db.commit()

    room = get_room_id(sender_id, receiver_id)

    emit('messages_seen', {
        'sender_id': sender_id
    }, room=room)


# -------------------- Run App --------------------
if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
