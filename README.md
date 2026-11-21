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
| Briefings | Morning briefing (7:00 AM) and evening wrap-up (9:30 PM) on Telegram and WhatsApp, with a voice note on Telegram. |
| Voice | Siri-style voice screen on the dashboard, plus Telegram and WhatsApp voice notes. |
| "Hey Bob" | Hands-free mode: say "Hey Bob" while the dashboard is open and he starts listening. |
| WhatsApp | Free alerts to your own number (CallMeBot), plus optional two-way chat with the WhatsApp Cloud API. |
| bKash | Your phone forwards bKash SMS; Mr. Bob tracks money in and out, your balance, and warns you when it's low. |
| Phone app | Install the dashboard on your home screen; it opens full-screen and works on weak connections. |
| 12-hour time | Every time is shown and spoken as 12-hour (3:00 PM). |
| Email drafts | He can write a Gmail draft for you. He never sends email or pays for anything himself. |
| Dashboard | iOS 26 "Liquid Glass" style, with Mr. Bob's photo as a living 3D card, today's widgets, chat, connections, activity log and a live monthly cost card. Can be added to your phone's home screen. |

## How it is built

```
Phone / browser ──► Dashboard (HTML, CSS, JS) ──► FastAPI backend
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
├─ frontend/             the Liquid Glass dashboard and Mr. Bob's photo
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
3. Copy the token into `TELEGRAM_BOT_TOKEN`. Leave `TELEGRAM_CHAT_ID` empty: Mr. Bob links your account himself (Step 3).
4. Make sure `OWNER_PHONE` is your number (`+8801787361208`).

### 1e. WhatsApp alerts (free)
1. Go to **callmebot.com → WhatsApp** and save their bot number in your phone contacts (the number is on that page; it can change).
2. From your WhatsApp (`+8801787361208`), send it: `I allow callmebot to send me messages`
3. It replies with your **API key**. Put it in `CALLMEBOT_APIKEY`.
From then on every alert and briefing also arrives on your WhatsApp. This free service is for personal use only, which is exactly this.

### 1f. Google: Gmail and Calendar
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
2. In Telegram, open your bot and send `/start`. Tap **📱 Share my number**. If it matches `OWNER_PHONE`, he replies **Linked! ✅**. Nothing to edit, no restart.
3. Send the bot "hi" or a voice note. He answers, and from now on alerts and briefings arrive there. Anyone else who finds your bot is ignored.

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
- Add the server redirect URI from Step 1f if you haven't, then connect Google again from the online dashboard.

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

## Step 5. Extras

### WhatsApp chat (optional, two-way)
CallMeBot only *sends* to you. To also *talk* to Mr. Bob on WhatsApp:
1. Go to **developers.facebook.com → My Apps → Create app**, choose the WhatsApp use case, and connect a business portfolio.
2. In **WhatsApp → API Setup** you get a free **test number**. Add `+8801787361208` as an allowed recipient.
3. Copy the **temporary access token** into `WHATSAPP_TOKEN` (later create a permanent System User token) and the **Phone number ID** into `WHATSAPP_PHONE_NUMBER_ID`.
4. **WhatsApp → Configuration → Webhook**: Callback URL `https://bob.yourdomain.com/api/whatsapp/webhook`, Verify token = the word you put in `WHATSAPP_VERIFY_TOKEN`. Click **Verify and save**, then subscribe to **messages**.
5. Save Mr. Bob's WhatsApp number in your phone and message him. He answers text and voice notes, only from your number.

Cost: messages *you* send are free. Since 1 October 2026 Meta charges for replies, but each number gets a free monthly allowance of service messages (1,000 at the time of writing), far more than one person uses.

### bKash tracking (SMS forwarding)
Mr. Bob can't read your SMS by himself; your phone forwards bKash messages to him.
1. Put a long random word in `SMS_WEBHOOK_TOKEN` and restart.
2. **Android:** install an SMS-to-webhook forwarder app from the Play Store (search "SMS forwarder webhook"). Make a rule:
   - Sender contains `bKash`
   - Method `POST`, URL `https://bob.yourdomain.com/api/sms?token=YOUR_TOKEN`
   - Body JSON: `{"from": "<sender>", "text": "<message>"}` (use the app's own placeholders for sender and message)
3. **iPhone:** Shortcuts → Automation → **Message**, sender bKash → action **Get contents of URL** (POST, same URL, JSON with `from` and `text`).
4. Send yourself a small bKash amount to test. It appears in **bKash this month** on the dashboard.

He understands received money, send money, cash in, cash out, payments, mobile recharge and bill payments. He warns you when the balance drops under `BKASH_LOW_BALANCE_BDT` or when you receive more than `BKASH_BIG_AMOUNT_BDT`, and you can ask him "bKash e koto taka ache?". Your SMS stay on your own server.

### "Hey Bob" hands-free
**Settings → "Hey Bob" hands-free → on.** While the dashboard is open (laptop on the desk, or the app on your phone), say **"Hey Bob"**. The voice screen opens, he listens, answers out loud, and goes back to waiting. This uses the browser's built-in speech recognition (Chrome, Edge or Safari) and only works while the page is open. A true always-on "Hey Bob" needs a small device such as a Raspberry Pi, which is a later project.

### Install as a phone app
Open the dashboard in Chrome (Android) or Safari (iPhone) → **Install app / Add to Home Screen**. He gets his own icon, opens full-screen, and still opens on a weak connection.

---

## Monthly cost (target ৳2,700)

| Item | About | Paid with |
|---|---|---|
| Server (4 GB VPS) | ৳1,300 | bKash |
| Claude (brain) | ৳600 | USD card, prepaid |
| OpenAI speech-to-text | ৳350 | USD card, prepaid |
| Domain | ৳150 (per month, paid yearly) | bKash |
| 15% VAT on USD payments | ৳140 | added by your bank |
| Voice, Telegram, WhatsApp alerts, bKash tracking, Groq backup, weather, database | ৳0 | — |

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
| Gmail stopped after a week | The Google app is still in Testing mode. Publish it (Step 1f), then reconnect. |
| Mic button missing | The page must be HTTPS (or localhost), and the browser must allow the microphone. |
| Telegram silent | Send `/start` and share your number again; check `OWNER_PHONE` and that Telegram is on in Settings. |
| No WhatsApp alerts | Check `CALLMEBOT_APIKEY` and `OWNER_PHONE`; redo the CallMeBot activation message. |
| bKash card empty | Check the forwarder app's URL and token; `docker compose logs bob` shows each `/api/sms` call. |
| Replies say "my brain is offline" | Check `ANTHROPIC_API_KEY` and your Claude credit, and add `GROQ_API_KEY` as a backup. |

## Ideas for later
- Always-on "Hey Bob" on a small device (Raspberry Pi with a custom wake word).
- Nagad and bank SMS tracking.
- A native phone app in the stores.

---

Made by **Jonayed Hossain** · Project Aethrix · Dhaka
