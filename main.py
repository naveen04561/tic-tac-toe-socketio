from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "naveen123"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        elif rooms[code]["members"] == 2:
            return render_template("home.html", error="Room is full.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        session["symbol"] = "X"
        session["chance"] = 1
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms or rooms[room]["members"] == 2:
        return redirect(url_for("home"))
    
    return render_template("room.html", name=session.get("name"), code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"],
        "symbol": data["symbol"],
        "chance": data["chance"]
    }

    socketio.emit('message',data=content,to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("update")
def update(data):
    room = session.get("room")
    if room not in rooms:
        return
    msg = {}
    if data["name"] != session.get("name"):
        session["chance"] = 1
        if data["symbol"] == "X":
            session["symbol"] = "O"
        else:
            session["symbol"] = "X"
    else:
        session["chance"] = 0

    msg["name"] = session.get("name")
    msg["symbol"] = session.get("symbol")
    msg["chance"] = session.get("chance")
    socketio.emit('update',data=msg,to=room)

@socketio.on("winner")
def winner(data):
    room = session.get("room")
    if room not in rooms:
        return
    socketio.emit('winner',data=data,to=room)

@socketio.on("connect")
def connect():
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    # send({"name": name, "message": ""}, to=room)
    rooms[room]["members"] += 1

    if rooms[room]['members'] == 1:
        socketio.emit('player',data={"message": "Waiting for player"},to=room)

    if rooms[room]['members'] == 2:
        socketio.emit('player',data={"message": "Two players joined"},to=room)

    print(f"{name} joined room {room}")
    print(rooms)

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)