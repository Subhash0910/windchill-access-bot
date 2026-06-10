"""Demo driver. Resets the mock queue, then drips new fake tasks into it.

  python demo.py reset    # restore the queue to its initial state
  python demo.py live     # reset, then inject a new task every 15 seconds
"""

import json
import sys
import time

QUEUE = "mock_data/queue.json"

INITIAL = {
    "tasks": [],
    "requests": {},
    "people": [
        {"id": 201, "name": "Sarah Mitchell", "primary_email": "sarah.mitchell@acme-aero.example"},
        {"id": 202, "name": "Rajesh Kumar", "primary_email": "rajesh.kumar@acme-aero.example"},
        {"id": 203, "name": "Linda Schmidt", "primary_email": "linda.schmidt@acme-aero.example", "disabled": True},
        {"id": 204, "name": "Tom Becker", "primary_email": "tom.becker@acme-aero.example"},
        {"id": 205, "name": "Priya Nair", "primary_email": "priya.nair@acme-aero.example"},
        {"id": 206, "name": "James O'Brien", "primary_email": "james.obrien@acme-aero.example"},
        {"id": 207, "name": "Maria Gonzalez", "primary_email": "maria.gonzalez@acme-aero.example"},
    ],
}

SCENARIOS = [
    ("Windchill PLM Access - Change access",
     "Hi team, please grant John Doe modify access to the Aero Structures Library. Thanks!"),
    ("Windchill PLM Access - Create account",
     "New joiner Emily Watson needs an account with read access to Engine Components Library."),
    ("Windchill PLM Access - Change access",
     "Please upgrade my license, I need write access in the Landing Gear Library for project X."),
    ("Windchill PLM Access - Change access",
     "Need access to the propulsion test data folder, manager approved verbally."),
    ("Windchill PLM Access - Create account",
     "Contractor onboarding: viewer access to Composites Library and Tooling Library please."),
]


def reset():
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(INITIAL, f, indent=2)
    print("Queue reset (0 tasks).")


def inject(n, subject, note):
    with open(QUEUE, encoding="utf-8") as f:
        data = json.load(f)
    task_id, req_id = 6000 + n, 91000 + n
    data["requests"][str(req_id)] = {"id": req_id, "subject": subject, "note": note}
    data["tasks"].append({
        "id": task_id,
        "template": "Windchill - Add data owner approver",
        "status": "assigned",
        "request_id": req_id,
    })
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f">>> new ticket arrived: task {task_id} - {note[:70]}...")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "live"
    reset()
    if cmd == "reset":
        return
    print("Injecting a new fake ticket every 15 seconds. Run `python bot.py` in "
          "another window. Ctrl+C to stop.\n")
    for n, (subject, note) in enumerate(SCENARIOS, start=1):
        inject(n, subject, note)
        time.sleep(15)
    print("\nAll demo tickets injected.")


if __name__ == "__main__":
    main()
