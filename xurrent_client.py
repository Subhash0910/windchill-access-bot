"""Xurrent API clients: a mock one (reads/writes a local JSON file, used for
the demo) and a live one (real REST calls). Both expose the same methods, so
bot.py never knows which it is talking to — going live is a config change."""

import json
import os
import urllib.request


class MockXurrentClient:
    """Simulates the Xurrent queue using mock_data/queue.json."""

    def __init__(self, queue_path):
        self.queue_path = queue_path

    def _load(self):
        with open(self.queue_path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_open_tasks(self, template_keyword):
        data = self._load()
        return [
            t for t in data["tasks"]
            if t["status"] == "assigned" and template_keyword.lower() in t["template"].lower()
        ]

    def get_request(self, request_id):
        return self._load()["requests"][str(request_id)]

    def find_person_by_email(self, email):
        for p in self._load()["people"]:
            if p["primary_email"].lower() == email.lower():
                return p
        return None

    def set_approver(self, task_id, person):
        data = self._load()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["approver"] = {"id": person["id"], "name": person["name"]}
        self._save(data)

    def add_note(self, task_id, text):
        data = self._load()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t.setdefault("notes", []).append(text)
        self._save(data)

    def complete_task(self, task_id):
        data = self._load()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "completed"
        self._save(data)


class LiveXurrentClient:
    """Real Xurrent REST API client. Endpoint paths follow the public docs
    (developer.xurrent.com); verify field names against your instance before
    first live run."""

    def __init__(self, base_url, account, token):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "X-Xurrent-Account": account,
            "Content-Type": "application/json",
        }

    def _call(self, method, path, body=None):
        url = self.base_url + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None

    def get_open_tasks(self, template_keyword):
        tasks = self._call("GET", "/tasks?status=assigned&fields=id,subject,template")
        return [t for t in tasks if template_keyword.lower() in (t.get("subject") or "").lower()]

    def get_request(self, request_id):
        return self._call("GET", f"/requests/{request_id}")

    def find_person_by_email(self, email):
        people = self._call("GET", f"/people?primary_email={email}")
        return people[0] if people else None

    def set_approver(self, task_id, person):
        self._call("PATCH", f"/tasks/{task_id}", {"approver": {"id": person["id"]}})

    def add_note(self, task_id, text):
        self._call("POST", f"/tasks/{task_id}/notes", {"text": text})

    def complete_task(self, task_id):
        self._call("PATCH", f"/tasks/{task_id}", {"status": "completed"})


def make_client(config):
    if config["mode"] == "mock":
        return MockXurrentClient(config["mock_queue_path"])
    live = config["live"]
    token = os.environ.get(live["token_env_var"], "")
    if not token:
        raise RuntimeError(f"Live mode needs the {live['token_env_var']} environment variable set.")
    return LiveXurrentClient(live["base_url"], live["account"], token)
