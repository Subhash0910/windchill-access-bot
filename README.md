# Windchill Access Bot (prototype)

Automates the **"Windchill - Add data owner approver"** task in Xurrent:
reads the request, finds the library name, looks up the owner in
`libraries.csv`, sets them as approver, and completes the task.
Today this step takes ~2 hours of queue latency; the bot does it in under
one poll cycle. Anything it cannot match **exactly** is left for a human
with an explanatory note — the bot never guesses.

> All data in this repo is **fictional** ("Acme Aerospace"). Built from
> public Xurrent API docs and generic ITSM/Windchill domain knowledge.

## How it works

```
WINDCHILL (prod)            SHARED LOCATION              YOUR MACHINE              XURRENT (cloud)
daily scheduled job  --->  libraries.csv          <---  bot reads file
(Phase 2; in Phase 1       (network drive /             bot polls API every  ---> REST API
 the CSV is maintained      SharePoint / OneDrive)      2 min, sets approver,<--- responses
 by hand)                                               completes task
```

- No system connects to any other system. Windchill drops a file; the bot
  reads it and works the Xurrent queue with the same access a team member has.
- All traffic is **outbound** from the bot machine to Xurrent. Nothing comes in.
- The data owner still approves personally. The bot only fills in *who* approves.

## Run the CLI demo

```
python bot.py --once        # single pass over the mock queue
python bot.py               # continuous polling (Ctrl+C to stop)
```

Live demo (two terminals):

```
T1:  python demo.py live    # resets queue, injects a fake ticket every 15s
T2:  python bot.py          # watch them get resolved
```

## Hosted web demo

See `webapp/` — FastAPI backend + static dashboard, deployable on Render
(single service) or Render+Vercel. Instructions in `webapp/DEPLOY.md`.

## Going live (when approved)

1. Get an API token scoped to the team's Xurrent account; set it as the
   `XURRENT_TOKEN` environment variable.
2. In `config.json` set `"mode": "live"`, fill in `live.account`, and bump
   `poll_interval_seconds` to 120.
3. Verify the endpoint/field names in `LiveXurrentClient` against your
   instance (developer.xurrent.com).
4. Replace `libraries.csv` with the real mapping.

Kill switch: set `"enabled": false` in `config.json`.
