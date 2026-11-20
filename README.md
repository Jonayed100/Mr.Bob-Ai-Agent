# Mr. Bob

**A personal AI agent. A Project Aethrix Work.**

Mr. Bob is a cute butler cat who keeps an eye on your day. He reads your Gmail and Google Calendar, watches the weather and air quality in Dhaka, reminds you of things, and tells you what matters on Telegram and on his own web dashboard. You can talk to him by voice or text in **English, বাংলা or Banglish**, and he answers in the same style, out loud.

---

## What he does

| Feature | How it works |
|---|---|
| Important email alerts | Checks Gmail every 10 minutes. Keyword rules sort most mail for free; only unclear emails go to Claude for a score. Important ones are sent to you on Telegram. |
| Calendar heads-up | Messages you 30 minutes before each event. |
| Weather and air | Hourly check (Open-Meteo, free). Warns about rain and unhealthy air. |
| Reminders | "Remind me to call Ammu at 8 PM" works by voice, text or Telegram. |
| Suggestions | Every 3 hours he writes up to 3 practical tips. Mark them Useful / Not useful and he learns. |
| Briefings | Morning briefing (7:00) and evening wrap-up (21:30) on Telegram, as text and a voice note. |
| Voice | Siri-style voice screen on the dashboard, plus Telegram voice notes. |
| Email drafts | He can write a Gmail draft for you. He never sends email or pays for anything himself. |
| Dashboard | iOS 26 "Liquid Glass" style, with a 3D cat, today's widgets, chat, connections, activity log and a live monthly cost card. Can be added to your phone's home screen. |

## How it is built

```
Phone / browser ──► Dashboard (HTML + Three.js) ──► FastAPI backend
Telegram ─────────────────────────────────────────►    │
                                                       ├─ Brain: Claude (tools) → backup: Groq free tier
                                                       ├─ Ears: OpenAI speech-to-text → backup: Groq Whisper
                                                       ├─ Voice: Microsoft Edge neural voices (free, has Bangla)
                                                       ├─ Gmail + Google Calendar (OAuth)
                                                       ├─ Weather + air quality (Open-Meteo)
                                                       ├─ Scheduler (APScheduler) for checks and briefings
                                                       └─ SQLite database (data/mrbob.db)
```

```
mr-bob/
├─ backend/app/
│  ├─ main.py            app start-up: database, scheduler, Telegram bot, dashboard
│  ├─ api.py             all /api routes used by the dashboard
│  ├─ config.py          settings from .env
│  ├─ models.py          database tables
│  ├─ agent/             brain (Claude + backup), tools, prompts, language detection
│  ├─ integrations/      Gmail, Calendar, Google sign-in, weather, Telegram
│  ├─ voice/             speech-to-text and text-to-speech
│  ├─ services/          email importance, checks, briefings, suggestions, costs
│  └─ worker/            scheduler and Telegram listener
├─ frontend/             the Liquid Glass dashboard and the 3D cat
├─ tests/                unit tests
├─ Dockerfile, docker-compose.yml, Caddyfile
└─ .env.example          every setting, explained
```

---

## Step 1. Get your keys (one time, about 30 minutes)

You need these before Mr. Bob can do anything. Put each one in `.env` (Step 2).

### 1a. Claude: the brain (paid, prepaid credit)
1. Go to **console.anthropic.com** and sign up.
2. **Settings → Billing → Buy credits.** Add your USD card and buy **$5**. Turn **auto-reload off** so it can never charge more.
3. **API keys → Create key.** Copy it into `ANTHROPIC_API_KEY`.

### 1b. OpenAI: speech-to-text (paid, prepaid credit)
1. Go to **platform.openai.com** and sign up.
2. **Billing → Add payment details**, buy **$5**, and **switch off auto-reload** (it is on by default).
3. **API keys → Create new secret key.** Copy it into `OPENAI_API_KEY`.

> Prepaid cards are usually refused. Use a dual-currency debit/credit card or a freelancer virtual card.

### 1c. Groq: free backup brain and ears
1. Go to **console.groq.com** and sign up (no card needed).
2. **API Keys → Create.** Copy it into `GROQ_API_KEY`.
If Claude or OpenAI are down or out of credit, Mr. Bob quietly switches to Groq.

### 1d. Telegram bot
1. In Telegram, open **@BotFather** and send `/newbot`.
2. Name it (for example `Mr. Bob`) and pick a username ending in `bot`.
3. Copy the token into `TELEGRAM_BOT_TOKEN`. Leave `TELEGRAM_CHAT_ID` empty for now (Step 5 fills it).

### 1e. Google: Gmail and Calendar
1. Go to **console.cloud.google.com** and create a project called `Mr Bob`.
2. **APIs & Services → Library**: enable **Gmail API** and **Google Calendar API**.
3. **OAuth consent screen**: User type **External**. App name `Mr. Bob`, your email as support and developer contact. Save.
4. On the same screen, under **Audience / Test users**, add your own Gmail address.
5. **Credentials → Create credentials → OAuth client ID → Web application.**
   Add an **Authorized redirect URI**:
   - for your computer: `http://localhost:8000/api/google/callback`
   - for the server: `https://bob.yourdomain.com/api/google/callback`
6. Copy the **Client ID** and **Client secret** into `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

> **Important:** while the app is in *Testing* mode, Google expires the login after **7 days**. Once everything works, go to the OAuth consent screen and click **Publish app** (status *In production*). Google will show a "this app isn't verified" screen when you connect: click **Advanced → Go to Mr. Bob**. That's normal for a personal app only you use.

---

## Step 2. Run it on your computer first

You need Python 3.11+.

```bash
git clone https://github.com/Jonayed100/Mr.Bob-Ai-Agent.git
cd Mr.Bob-Ai-Agent

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then open .env and paste your keys
uvicorn app.main:app --app-dir backend --reload
```

Open **http://localhost:8000**, type your `DASHBOARD_PASSWORD`, and you'll see Mr. Bob.

What to expect:
- The log says `Scheduler started`, `Telegram bot listening` and `Mr. Bob is awake`.
- Weather appears within a few seconds.
- The microphone works on `localhost`. On other addresses it needs HTTPS (Step 4 sets that up).

Run the tests any time with `pytest`.

---

## Step 3. Connect Google and Telegram

1. On the dashboard, go to **Settings → Google account → Connect**. Sign in, allow access, and you come back to the dashboard. Gmail and Calendar now fill in.
2. In Telegram, open your bot and send `/start`. It replies with **your chat id**. Put that number in `TELEGRAM_CHAT_ID` in `.env` and restart Mr. Bob.
3. Send the bot "hi" or a voice note. He answers, and from now on alerts and briefings arrive there. Only your chat id gets answers; anyone else is ignored.

---

## Step 4. Put him online (server + domain)

### 4a. Buy a server (pay with bKash)
Any Bangladeshi or international VPS works. Pick **Ubuntu 22.04 or 24.04, 2–4 GB RAM, full root access**. Most local hosts take bKash at checkout. You'll get an IP address and a root password by email.

### 4b. Point a domain at it
Buy a domain (local registrars take bKash), then in its DNS settings add:

| Type | Name | Value |
|---|---|---|
| A | `bob` | your server's IP |

So `bob.yourdomain.com` points to your server. It can take 5–30 minutes to work.

### 4c. Install and start
Log in to the server (`ssh root@YOUR_IP`) and run:

```bash
curl -fsSL https://get.docker.com | sh          # installs Docker

git clone https://github.com/Jonayed100/Mr.Bob-Ai-Agent.git
cd Mr.Bob-Ai-Agent
```

The repo is private, so `git clone` asks for a username and password. Use your GitHub username and a **personal access token** (GitHub → Settings → Developer settings → Fine-grained tokens, with read access to this repo) as the password.

```bash
cp .env.example .env
nano .env        # paste your keys, then set:
                 #   PUBLIC_URL=https://bob.yourdomain.com
                 #   DOMAIN=bob.yourdomain.com
                 #   a strong DASHBOARD_PASSWORD and SECRET_KEY
docker compose up -d --build
```

What happens:
- `bob` is the app. `caddy` gets a free HTTPS certificate for your domain automatically.
- After a minute, open **https://bob.yourdomain.com** on your phone or laptop.
- Add the server redirect URI from Step 1e if you haven't, then connect Google again from the online dashboard.

Useful commands:
```bash
docker compose logs -f bob      # watch what Mr. Bob is doing
docker compose restart bob      # after changing .env
git pull && docker compose up -d --build    # update to the newest code
```

Your data lives in the `data/` folder on the server. Back it up now and then.

### 4d. Put him on your phone's home screen
Open the dashboard in your phone's browser → **Share / menu → Add to Home Screen**. He opens full-screen like an app, and the mic works because the site is HTTPS.

---

## Monthly cost (target ৳2,700)

| Item | About | Paid with |
|---|---|---|
| Server (4 GB VPS) | ৳1,300 | bKash |
| Claude (brain) | ৳600 | USD card, prepaid |
| OpenAI speech-to-text | ৳350 | USD card, prepaid |
| Domain | ৳150 (per month, paid yearly) | bKash |
| 15% VAT on USD payments | ৳140 | added by your bank |
| Voice, Telegram, Groq backup, weather, database | ৳0 | — |

The dashboard's **Monthly cost** card shows real spending: every Claude and speech-to-text call is recorded. Things that keep it low:
- Keyword rules decide most emails without the AI.
- `CLAUDE_MODEL=claude-haiku-4-5` is fast and cheap. Change it in `.env` if you want a bigger model.
- Raise `GMAIL_CHECK_MINUTES` to 15 or 20 to spend less.
- Keep auto-reload off on both AI accounts, so the bill can never go over what you loaded.

---

## Settings you might change

All in `.env` (restart after changing):

- `MORNING_BRIEFING_TIME`, `EVENING_SUMMARY_TIME`: when briefings arrive.
- `TTS_VOICE_*`: Mr. Bob's voices. Other Bangla voice: `bn-BD-NabanitaNeural`.
- `CITY`, `LATITUDE`, `LONGITUDE`: for weather.
- `STT_MODEL`: if OpenAI retires a speech model, put the new name here.

## Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard says "Can't reach Mr. Bob" | `docker compose logs bob` and look for the error. Usually a typo in `.env`. |
| Google says `redirect_uri_mismatch` | The URI in Google Cloud must exactly equal `PUBLIC_URL` + `/api/google/callback`. |
| Gmail stopped after a week | The Google app is still in Testing mode. Publish it (Step 1e), then reconnect. |
| Mic button missing | The page must be HTTPS (or localhost), and the browser must allow the microphone. |
| Telegram silent | Check `TELEGRAM_CHAT_ID`, and that Telegram is switched on in Settings. |
| Replies say "my brain is offline" | Check `ANTHROPIC_API_KEY` and your Claude credit, and add `GROQ_API_KEY` as a backup. |

## Ideas for later
- "Hey Bob" wake word with a small always-on device (Raspberry Pi + openWakeWord).
- bKash SMS and WhatsApp alerts.
- A native phone app.

---

Made by **Jonayed Hossain** · Project Aethrix · Dhaka
