"""Session Tracking microservice (CS361).

Run with:  python session_service.py
Listens on http://127.0.0.1:8363 and speaks JSON over HTTP.
Sessions are kept in memory, so they are cleared when the service stops.                                #4
"""
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify

PORT = 8363

app = Flask(__name__)
sessions = {}
lock = Lock()


def now():
    return datetime.now(timezone.utc)


def to_text(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def session_details(session_id, session):
    start, end = session["start"], session["end"]
    return {
        "session_id": session_id,
        "start_time": to_text(start),
        "end_time": to_text(end) if end else None,
        "duration_seconds": round((end - start).total_seconds()) if end else None,
    }


@app.route("/sessions", methods=["POST"])
def start_session():                                                                                    #2
    with lock:
        session_id = "s{:03d}".format(len(sessions) + 1)
        sessions[session_id] = {"start": now(), "end": None}
        start_time = to_text(sessions[session_id]["start"])
    return jsonify({"session_id": session_id, "start_time": start_time}), 201


@app.route("/sessions/<session_id>/end", methods=["POST"])
def end_session(session_id):
    with lock:
        session = sessions.get(session_id)
        if session is None:
            return jsonify({"error": "Session not found"}), 404
        if session["end"] is not None:
            return jsonify({"error": "Session already ended"}), 409
        session["end"] = now()
        details = session_details(session_id, session)
    return jsonify(details), 200


@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    with lock:
        session = sessions.get(session_id)
        if session is None:
            return jsonify({"error": "Session not found"}), 404
        details = session_details(session_id, session)
    return jsonify(details), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def wrong_method(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT)