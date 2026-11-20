import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room

RUNNERS = ["Gabby", "Maverick", "Vincent", "Jackson"]
EVENT_CODE = os.environ.get("EVENT_CODE", "")
ORGANIZER_CODE = os.environ.get("ORGANIZER_CODE", "")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
socketio = SocketIO(app, cors_allowed_origins=[])

# Latest locations live only in memory and are cleared when the service restarts.
latest_locations = {}

@app.get("/")
def runner_page():
    return render_template("runner.html", runners=RUNNERS)

@app.get("/organizer")
def organizer_page():
    return render_template("organizer.html")

@app.get("/health")
def health():
    return jsonify(status="ok")

@socketio.on("join_runner")
def handle_join_runner(data):
    if not EVENT_CODE or not isinstance(data, dict) or data.get("event_code") != EVENT_CODE:
        emit("access_error", {"message": "The event code is incorrect."})
        return
    runner = data.get("runner")
    if runner not in RUNNERS:
        emit("access_error", {"message": "Please choose a valid runner name."})
        return
    join_room("runners")
    emit("share_ready", {"runner": runner})

@socketio.on("join_organizer")
def handle_join_organizer(data):
    if not ORGANIZER_CODE or not isinstance(data, dict) or data.get("organizer_code") != ORGANIZER_CODE:
        emit("access_error", {"message": "The organizer code is incorrect."})
        return
    join_room("organizers")
    emit("initial_locations", list(latest_locations.values()))

@socketio.on("runner_location")
def handle_runner_location(data):
    if not isinstance(data, dict):
        return
    runner = data.get("runner")
    if runner not in RUNNERS or data.get("event_code") != EVENT_CODE:
        return
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
        accuracy = float(data.get("accuracy", 0))
    except (TypeError, ValueError):
        return
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return
    location = {
        "runner": runner,
        "lat": lat,
        "lng": lng,
        "accuracy": round(max(0, accuracy)),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    latest_locations[runner] = location
    socketio.emit("location_update", location, room="organizers")

@socketio.on("runner_stopped")
def handle_runner_stopped(data):
    if not isinstance(data, dict):
        return
    runner = data.get("runner")
    if runner in RUNNERS and data.get("event_code") == EVENT_CODE:
        latest_locations.pop(runner, None)
        socketio.emit("runner_stopped", {"runner": runner}, room="organizers")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
