"""Windchill Access Bot — automates the 'Add data owner approver' task.

Loop: poll Xurrent for open tasks -> read the request text -> find a known
library name in it -> look up the owner in libraries.csv -> set them as
approver and complete the task. Anything uncertain is left for a human with
a note. The bot never guesses.

Run:  python bot.py          (continuous, Ctrl+C to stop)
      python bot.py --once   (single pass, good for testing/demo)
Kill switch: set "enabled": false in config.json — takes effect next cycle.
"""

import csv
import json
import sys
import time
from datetime import datetime

from xurrent_client import make_client

CONFIG_PATH = "config.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_library_owners(csv_path):
    owners = {}
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            owners[row["library_name"].strip().lower()] = {
                "library": row["library_name"].strip(),
                "name": row["owner_name"].strip(),
                "email": row["owner_email"].strip(),
            }
    return owners


def find_library_in_text(text, owners):
    """Exact known-name matching only (longest name first). No guessing:
    if no known library name appears in the text, return None."""
    text_lower = text.lower()
    for key in sorted(owners, key=len, reverse=True):
        if key in text_lower:
            return owners[key]
    return None


def log(config, message):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {message}"
    print(line)
    with open(config["log_file"], "a", encoding="utf-8") as f:
        f.write(line + "\n")


def process_task(client, config, owners, task):
    task_id = task["id"]
    request = client.get_request(task["request_id"])
    text = f"{request.get('subject', '')} {request.get('note', '')}"

    match = find_library_in_text(text, owners)
    if match is None:
        client.add_note(task_id, "[bot] No known library name found in the request "
                                 "- leaving for manual handling.")
        log(config, f"task {task_id}: NO MATCH -> left for human (request {request['id']})")
        return

    person = client.find_person_by_email(match["email"])
    if person is None:
        client.add_note(task_id, f"[bot] Library '{match['library']}' maps to "
                                 f"{match['email']}, but no matching person found in "
                                 f"Xurrent - leaving for manual handling.")
        log(config, f"task {task_id}: owner {match['email']} not in Xurrent -> left for human")
        return

    if person.get("disabled", False):
        client.add_note(task_id, f"[bot] Library '{match['library']}' maps to "
                                 f"{person['name']} ({match['email']}), but that account "
                                 f"is DISABLED (likely left the org). Leaving for manual "
                                 f"handling - please update libraries.csv with the new owner.")
        log(config, f"task {task_id}: owner {match['email']} is DISABLED -> left for human, CSV needs update")
        return

    client.set_approver(task_id, person)
    client.add_note(task_id, f"[bot] Approver auto-set: '{match['library']}' -> "
                             f"{person['name']} ({match['email']}).")
    client.complete_task(task_id)
    log(config, f"task {task_id}: DONE  '{match['library']}' -> {person['name']} "
                f"({match['email']}), task completed")


def run_cycle():
    config = load_config()           # reloaded every cycle: kill switch + live edits
    if not config.get("enabled", False):
        print("Bot is disabled in config.json (kill switch). Skipping cycle.")
        return config

    client = make_client(config)
    owners = load_library_owners(config["csv_path"])
    tasks = client.get_open_tasks(config["task_template_keyword"])

    if tasks:
        log(config, f"poll: {len(tasks)} open task(s) found")
        for task in tasks:
            try:
                process_task(client, config, owners, task)
            except Exception as e:               # one bad task must not kill the loop
                log(config, f"task {task['id']}: ERROR {e!r} -> left for human")
    return config


def main():
    once = "--once" in sys.argv
    print(f"Windchill Access Bot starting ({'single pass' if once else 'continuous'}) ...")
    while True:
        config = run_cycle()
        if once:
            break
        time.sleep(config.get("poll_interval_seconds", 120))


if __name__ == "__main__":
    main()
