import os
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit, join_room

RUNNERS = ["Maverick", "Gabby", "Vincent", "Chris", "Emily", "Grace", "Jackson"]
RUNNER_LABELS = {
    "Maverick": "M.M",
    "Gabby": "G.L",
    "Vincent": "V.L",
    "Chris": "C.M",
    "Emily": "E.M",
    "Grace": "G.M",
    "Jackson": "J.M",
}
EVENT_CODE = os.environ.get("EVENT_CODE", "")
ORGANIZER_CODE = os.environ.get("ORGANIZER_CODE", "")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
socketio = SocketIO(app, cors_allowed_origins=[])

# Latest runner stats are held in memory and reset when the service restarts.
latest_locations = {}
runner_sessions = {}

def distance_miles(lat1, lng1, lat2, lng2):
    radius_miles = 3958.7613
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * radius_miles * atan2(sqrt(a), sqrt(1 - a))

def make_stats(runner, lat, lng, accuracy):
    now = datetime.now(timezone.utc)
    session = runner_sessions.get(runner)
    if session is None:
        session = {"started_at": now, "last_lat": lat, "last_lng": lng, "miles": 0.0}
        runner_sessions[runner] = session
    else:
        step = distance_miles(session["last_lat"], session["last_lng"], lat, lng)
        # Ignore implausible GPS jumps; keep the last valid point for the next update.
        if step <= 0.25 and accuracy <= 100:
            session["miles"] += step
        session["last_lat"], session["last_lng"] = lat, lng

    elapsed = max(0, int((now - session["started_at"]).total_seconds()))
    miles = session["miles"]
    pace_seconds = int(elapsed / miles) if miles >= 0.05 else None
    pace = f"{pace_seconds // 60}:{pace_seconds % 60:02d}" if pace_seconds is not None else "—"
    return {
        "runner": runner, "lat": lat, "lng": lng,
        "accuracy": round(max(0, accuracy)),
        "updated_at": now.isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed": f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}",
        "miles": round(miles, 2), "pace": pace
    }

@app.get("/")
def runner_page():
    return render_template("runner.html", runners=RUNNERS, runner_labels=RUNNER_LABELS)

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
    location = make_stats(runner, lat, lng, accuracy)
    latest_locations[runner] = location
    socketio.emit("location_update", location, room="organizers")
    emit("runner_stats", location)

@socketio.on("runner_stopped")
def handle_runner_stopped(data):
    if not isinstance(data, dict):
        return
    runner = data.get("runner")
    if runner in RUNNERS and data.get("event_code") == EVENT_CODE:
        latest_locations.pop(runner, None)
        runner_sessions.pop(runner, None)
        socketio.emit("runner_stopped", {"runner": runner}, room="organizers")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
