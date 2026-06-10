"""Windchill Access Bot — demo backend (FastAPI).

Hosts a simulated Xurrent queue in memory plus the bot engine running as a
background loop. The frontend dashboard injects fake tickets and watches the
bot resolve them. All data is fictional; nothing connects to any real system.

Run locally:   uvicorn main:app --reload
Render start:  uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import itertools
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

# ---------------------------------------------------------------- fake data

LIBRARIES = {
    "aero structures library":     {"library": "Aero Structures Library",     "owner": "Sarah Mitchell",  "email": "sarah.mitchell@acme-aero.example"},
    "engine components library":   {"library": "Engine Components Library",   "owner": "Rajesh Kumar",    "email": "rajesh.kumar@acme-aero.example"},
    "landing gear library":        {"library": "Landing Gear Library",        "owner": "Linda Schmidt",   "email": "linda.schmidt@acme-aero.example"},
    "fasteners standard library":  {"library": "Fasteners Standard Library",  "owner": "Tom Becker",      "email": "tom.becker@acme-aero.example"},
    "electrical harness library":  {"library": "Electrical Harness Library",  "owner": "Priya Nair",      "email": "priya.nair@acme-aero.example"},
    "composites library":          {"library": "Composites Library",          "owner": "James O'Brien",   "email": "james.obrien@acme-aero.example"},
    "tooling library":             {"library": "Tooling Library",             "owner": "Maria Gonzalez",  "email": "maria.gonzalez@acme-aero.example"},
}

PEOPLE = {
    "sarah.mitchell@acme-aero.example": {"id": 201, "name": "Sarah Mitchell",  "disabled": False},
    "rajesh.kumar@acme-aero.example":   {"id": 202, "name": "Rajesh Kumar",    "disabled": False},
    "linda.schmidt@acme-aero.example":  {"id": 203, "name": "Linda Schmidt",   "disabled": True},   # left the org
    "tom.becker@acme-aero.example":     {"id": 204, "name": "Tom Becker",      "disabled": False},
    "priya.nair@acme-aero.example":     {"id": 205, "name": "Priya Nair",      "disabled": False},
    "james.obrien@acme-aero.example":   {"id": 206, "name": "James O'Brien",   "disabled": False},
    "maria.gonzalez@acme-aero.example": {"id": 207, "name": "Maria Gonzalez",  "disabled": False},
}

SCENARIOS = [
    {"subject": "Windchill PLM Access - Change access",
     "note": "Hi team, please grant John Doe modify access to the Aero Structures Library. He moved to the wing design group."},
    {"subject": "Windchill PLM Access - Create account",
     "note": "New joiner Emily Watson needs a Windchill account with read access to Engine Components Library and a viewer license."},
    {"subject": "Windchill PLM Access - Change access",
     "note": "Please upgrade my license, I need write access in the Landing Gear Library for project X."},
    {"subject": "Windchill PLM Access - Change access",
     "note": "Need access to the propulsion test data folder, my manager already approved verbally."},
    {"subject": "Windchill PLM Access - Create account",
     "note": "Contractor onboarding: viewer access to Composites Library and Tooling Library please."},
    {"subject": "Windchill PLM Access - Change access",
     "note": "Requesting checkout rights on the Fasteners Standard Library for the brake assembly work package."},
    {"subject": "Windchill PLM Access - Change access",
     "note": "Add me to the Electrical Harness Library with modify access, ref project Falcon."},
]

MANUAL_BASELINE_MINUTES = 120  # what this task costs today, per ticket

# ---------------------------------------------------------------- state

class State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.enabled = True
        self.tasks = []
        self.log = []
        self.ids = itertools.count(6001)
        self.scenario_cycle = itertools.cycle(range(len(SCENARIOS)))

S = State()

def now():
    return datetime.now(timezone.utc).isoformat()

def log_line(msg):
    S.log.append({"ts": now(), "msg": msg})
    S.log = S.log[-200:]

def add_ticket(subject, note):
    task = {
        "id": next(S.ids),
        "template": "Windchill - Add data owner approver",
        "status": "assigned",
        "request": {"subject": subject, "note": note},
        "approver": None,
        "notes": [],
        "created_at": now(),
        "resolved_at": None,
        "outcome": None,   # auto | human
    }
    S.tasks.append(task)
    log_line(f"new ticket: task {task['id']} - {note[:80]}")
    return task

# ---------------------------------------------------------------- bot engine

def find_library(text):
    text = text.lower()
    for key in sorted(LIBRARIES, key=len, reverse=True):
        if key in text:
            return LIBRARIES[key]
    return None

def process_task(task):
    text = f"{task['request']['subject']} {task['request']['note']}"
    match = find_library(text)

    if match is None:
        task["notes"].append("[bot] No known library name found in the request - leaving for manual handling.")
        task["outcome"] = "human"
        log_line(f"task {task['id']}: NO MATCH -> left for human")
        return

    person = PEOPLE.get(match["email"])
    if person is None:
        task["notes"].append(f"[bot] Owner {match['email']} not found in Xurrent - leaving for manual handling.")
        task["outcome"] = "human"
        log_line(f"task {task['id']}: owner not in Xurrent -> left for human")
        return

    if person["disabled"]:
        task["notes"].append(f"[bot] Library '{match['library']}' maps to {person['name']}, but that account is "
                             f"DISABLED (likely left the org). Leaving for manual handling - update libraries.csv.")
        task["outcome"] = "human"
        log_line(f"task {task['id']}: owner {person['name']} DISABLED -> left for human, CSV needs update")
        return

    task["approver"] = {"id": person["id"], "name": person["name"], "email": match["email"]}
    task["notes"].append(f"[bot] Approver auto-set: '{match['library']}' -> {person['name']} ({match['email']}).")
    task["status"] = "completed"
    task["resolved_at"] = now()
    task["outcome"] = "auto"
    log_line(f"task {task['id']}: DONE '{match['library']}' -> {person['name']}, task completed")

async def bot_loop():
    while True:
        if S.enabled:
            pending = [t for t in S.tasks if t["status"] == "assigned" and t["outcome"] is None]
            for t in pending:
                await asyncio.sleep(1.2)   # dramatic pause so the dashboard shows it happening
                process_task(t)
        await asyncio.sleep(2)

# ---------------------------------------------------------------- api

app = FastAPI(title="Windchill Access Bot - Demo")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    asyncio.create_task(bot_loop())
    log_line("bot engine started (demo mode, fictional data)")

class NewTicket(BaseModel):
    subject: str | None = None
    note: str | None = None

class Toggle(BaseModel):
    enabled: bool

@app.get("/api/state")
def get_state():
    auto = [t for t in S.tasks if t["outcome"] == "auto"]
    human = [t for t in S.tasks if t["outcome"] == "human"]
    minutes_saved = len(auto) * MANUAL_BASELINE_MINUTES
    return {
        "enabled": S.enabled,
        "tasks": list(reversed(S.tasks)),
        "log": list(reversed(S.log)),
        "stats": {
            "total": len(S.tasks),
            "auto_resolved": len(auto),
            "left_for_human": len(human),
            "pending": len([t for t in S.tasks if t["outcome"] is None]),
            "minutes_saved": minutes_saved,
            "baseline_minutes_per_ticket": MANUAL_BASELINE_MINUTES,
        },
        "libraries": [v | {"disabled": PEOPLE[v["email"]]["disabled"]} for v in LIBRARIES.values()],
    }

@app.post("/api/tickets")
def create_ticket(body: NewTicket):
    if body.note:
        return add_ticket(body.subject or "Windchill PLM Access - Change access", body.note)
    scenario = SCENARIOS[next(S.scenario_cycle)]
    return add_ticket(scenario["subject"], scenario["note"])

@app.post("/api/reset")
def reset():
    S.reset()
    log_line("queue reset")
    return {"ok": True}

@app.post("/api/toggle")
def toggle(body: Toggle):
    S.enabled = body.enabled
    log_line(f"kill switch: bot {'ENABLED' if S.enabled else 'DISABLED'}")
    return {"enabled": S.enabled}

# ------------------------------------------------- serve frontend (optional)
# If ../frontend exists (single-service deploy on Render), serve it directly,
# so one URL gives the full demo. On a split deploy, Vercel serves it instead.

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND):
    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND, "index.html"))
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
