# Deploying the demo (free hosting)

## Option 1 — everything on Render (one link, recommended)

1. render.com -> New -> Web Service -> connect this GitHub repo
2. Settings:
   - Root Directory: `webapp/backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: Free
3. Deploy. The demo is live at `https://<name>.onrender.com`.

Caveat (free tier): sleeps after ~15 min idle, ~30-60s to wake.
Open the link 2 minutes before your demo meeting.

## Option 2 — frontend on Vercel + backend on Render

1. Backend on Render as above; note the URL.
2. Vercel -> New Project -> same repo, Root Directory `webapp/frontend`,
   preset Other.
3. Open: `https://<name>.vercel.app/?api=https://<backend>.onrender.com`

## Demo script

1. Open link -> empty queue, bot active
2. "+ New ticket arrives" a few times -> auto-resolved in ~2s each
3. Landing Gear ticket -> disabled owner caught, left for human
4. Propulsion ticket -> no known library -> untouched, "the bot never guesses"
5. Type a custom request -> resolved live
6. Kill switch -> tickets pile up; restart -> bot catches up
7. Stats bar: every green ticket is ~2 hours of latency removed

All data is fictional.
