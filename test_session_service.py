"""Test program for the Session Tracking microservice.

Start the service first (python session_service.py), then run:
    python test_session_service.py          short run, about 3 seconds
    python test_session_service.py --full   also waits a real 60 seconds                                    #4
"""
import sys
import time

import requests

BASE = "http://127.0.0.1:8363"
failures = 0


def check(description, condition):
    global failures
    print(("PASS: " if condition else "FAIL: ") + description)
    if not condition:
        failures += 1


def show(label, response):
    print("\n>>> " + label)
    print("<<< {} {}".format(response.status_code, response.json()))


delay = 60 if "--full" in sys.argv else 2

# Story 1: Start Session. The service returns a session ID.
response = requests.post(BASE + "/sessions")                                                                #1
show("POST /sessions", response)
data = response.json()                                                                                      #3
check("start returns 201 with a session_id and start_time",
      response.status_code == 201 and "session_id" in data and "start_time" in data)

# Reliability: five consecutive starts give five distinct IDs.
ids = [requests.post(BASE + "/sessions").json()["session_id"] for _ in range(5)]
print("\nFive more starts gave IDs:", ids)
check("five consecutive starts give five distinct session IDs", len(set(ids)) == 5)

# Story 2: End Session. Duration should match the time we waited.
session_id = requests.post(BASE + "/sessions").json()["session_id"]
print("\nWaiting {} seconds before ending session {}...".format(delay, session_id))
time.sleep(delay)
response = requests.post("{}/sessions/{}/end".format(BASE, session_id))
show("POST /sessions/{}/end".format(session_id), response)
ended = response.json()
check("end returns 200 with end_time and duration_seconds",
      response.status_code == 200 and ended.get("end_time") and ended.get("duration_seconds") is not None)
check("duration is within 1 second of the {} seconds waited".format(delay),
      abs(ended["duration_seconds"] - delay) <= 1)

# Story 3: Retrieve Session. A completed session returns start, end, and duration.
response = requests.get("{}/sessions/{}".format(BASE, session_id))
show("GET /sessions/{}".format(session_id), response)
check("lookup returns the same details as the end call",
      response.status_code == 200 and response.json() == ended)

# Errors: unknown IDs get a 404 with an error message.
response = requests.get(BASE + "/sessions/s999999")
show("GET /sessions/s999999", response)
check("unknown ID on lookup returns 404 with an error",
      response.status_code == 404 and response.json() == {"error": "Session not found"})

response = requests.post(BASE + "/sessions/s999999/end")
show("POST /sessions/s999999/end", response)
check("unknown ID on end returns 404 with an error", response.status_code == 404)

# Fault tolerance: the service still works after those errors, without a restart.
response = requests.get("{}/sessions/{}".format(BASE, session_id))
show("GET /sessions/{} (after the errors)".format(session_id), response)
check("a valid lookup still works after an unknown ID", response.status_code == 200)

# Ending a session twice is rejected and does not change the first result.
response = requests.post("{}/sessions/{}/end".format(BASE, session_id))
show("POST /sessions/{}/end (second time)".format(session_id), response)
check("ending an already-ended session returns 409", response.status_code == 409)

print("\n{} check(s) failed.".format(failures) if failures else "\nAll checks passed.")
sys.exit(1 if failures else 0)