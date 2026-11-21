# Mr. Bob

**A personal AI agent. A Project Aethrix Work.**

![CI](https://github.com/Jonayed100/Mr.Bob-Ai-Agent/actions/workflows/ci.yml/badge.svg) ![Version](https://img.shields.io/badge/version-2.2.0-e0142f) ![Python](https://img.shields.io/badge/python-3.12-1d1d1f)

Mr. Bob is a cute butler cat who keeps an eye on your day. He reads your Gmail and Google Calendar, watches the weather and air quality in Dhaka, reminds you of things, and tells you what matters on Telegram and on his own web dashboard. You can talk to him by voice or text in **English, বাংলা or Banglish**, and he answers in the same style, out loud.

---

## What he does

Mr. Bob is your **friend and personal manager**. The website is the main home; Telegram, WhatsApp and the phone app are extra ways to reach him.

| Part | What it does |
|---|---|
| **Reminders** | Add reminders with a **date and time**, mark them ⭐ important, repeat them daily / weekly / monthly, add notes, edit, snooze, tick off. At the right time Mr. Bob pops up on the website and **says it out loud**, and also messages you on Telegram, WhatsApp and the phone app. You can also just say *“Remind me to call Ammu tomorrow at 8 PM.”* |
| **Night report** | Say **“Hey Mr. Bob, tell me about my important tasks”** (or *“আমার আজকের রিপোর্ট দাও”*). He goes through your day **part by part**, most urgent first, and explains each one: what it is, why it matters, what to do and by when. Important parts are marked. Every night at 9:30 PM he does this by himself too. |
| **Reports** | Every briefing is saved in the **Reports** section of the website, one per day, so you can read or listen again later. The night report is also sent to Telegram and WhatsApp with a link. |
| **Memory** | Talk to him like a friend. He **remembers** people, dates, plans, goals and what you like, and uses it naturally later. See and edit everything he remembers in the **Memory** section. |
| **Talk to him** | **Tap Bob's photo and talk.** He listens, and when you stop he answers out loud. Tap again to keep talking. |
| **Language** | Speak English, he answers in English. Speak Bangla, he answers in Bangla. Both in voice. |
| **Natural voice** | An expressive, human-sounding voice (OpenAI) that speaks warmly and calmly, with a native Bangladeshi voice for Bangla. Free voices are the automatic backup, and if no voice can reach the phone, the browser's own voice reads the reply so he is never silent. |
| **Gmail** | Checks every 10 minutes. Keyword rules sort most mail for free; only unclear emails go to Claude. Important ones are flagged and sent to you. He can save draft replies (never sends). |
| **WhatsApp & Telegram** | Alerts, reminders and the night report arrive there. Chat by text or voice notes; send `/report` on Telegram for tonight's report. |
| **Calendar, weather, bKash** | Calendar heads-up 30 minutes before events, rain and air-quality warnings, bKash money in/out from SMS. |
| **“Hey Mr. Bob”** | Hands-free mode on the website: say “Hey Mr. Bob” while the page is open. |
| **Dashboard** | iOS 26 Liquid Glass design with pages for Home, Reminders, Reports, Memory and Settings, plus a Siri-style voice screen. 12-hour time everywhere. |

## How it is built

```
Phone / browser ──► Dashboard (HTML, CSS, JS) ──► FastAPI backend
Telegram ─────────────────────────────────────────►    │
                                                       ├─ Brain: Claude (tools) → backup: Groq free tier
                                                       ├─ Ears: OpenAI speech-to-text → backup: Groq Whisper
                                                       ├─ Voice: OpenAI natural voice → backup: Edge neural voices (has Bangla)
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
│  ├─ security.py        login sessions (tied to your password)
│  ├─ ratelimit.py       locks out password guessing
│  ├─ models.py          database tables
│  ├─ agent/             brain (Claude + backup), tools, prompts, language and briefing detection
│  ├─ integrations/      Gmail, Calendar, Google sign-in, weather, Telegram
│  ├─ voice/             speech-to-text and text-to-speech
│  ├─ services/          reminders, memory, night report, email importance, checks, notify, costs
│  ├─ migrations.py      upgrades an existing database when new fields are added
│  └─ worker/            scheduler and Telegram listener
├─ frontend/             the Liquid Glass dashboard and Mr. Bob's photo
├─ mobile/               the Android/iPhone app (React Native + Expo), see mobile/README.md
├─ tests/                unit tests
├─ .github/workflows/    CI: lint, tests, JavaScript check and Docker build on every push
├─ Dockerfile, docker-compose.yml, Caddyfile
└─ .env.example          every setting, explained
```

---

## Free mode: ৳0 a month

Mr. Bob runs completely free out of the box. `.env.example` is already set up for it.

| Part | Free service | Limit (plenty for one person) |
|---|---|---|
| Brain, with all tools (reminders, memory, Gmail, calendar) | **Groq** `gpt-oss-120b` | about 1,000 messages a day |
| Background jobs (email sorting, reports) | **Groq** `gpt-oss-20b` | its own separate quota |
| Ears (speech-to-text, Bangla + English) | **Groq Whisper** | about 8 hours of audio a day |
| Voice | **Microsoft Edge neural voices**, native Bangladeshi voice for Bangla | free |
| Server, running 24/7 | **Oracle Cloud Always Free** ARM VM | 2 CPUs + 12 GB RAM is enough |
| Web address with HTTPS | **DuckDNS** (`yourname.duckdns.org`) + Caddy | free |
| Telegram, WhatsApp alerts, Gmail, Calendar, weather | free | |

Free vs paid: the free brain is a little less clever than Claude and the free voice sounds less human than OpenAI's, but everything works the same. To upgrade later, add `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` (and `TTS_PROVIDER=openai`) to `.env` and restart. Nothing else changes.

If you hit Groq's limit (very heavy use in one day), Mr. Bob says so and works again a minute later; the daily limit resets every day.

**For free mode, you only need Steps 1c to 1f.** Skip 1a and 1b. For the server, follow **Step 4 (free)**.

## Step 1. Get your keys (one time, about 30 minutes)

You need these before Mr. Bob can do anything. Put each one in `.env` (Step 2).

### 1a. Claude: better brain (paid upgrade, skip for free mode)
1. Go to **console.anthropic.com** and sign up.
2. **Settings → Billing → Buy credits.** Add your USD card and buy **$5**. Turn **auto-reload off** so it can never charge more.
3. **API keys → Create key.** Copy it into `ANTHROPIC_API_KEY`.

### 1b. OpenAI: better ears and natural voice (paid upgrade, skip for free mode)
1. Go to **platform.openai.com** and sign up.
2. **Billing → Add payment details**, buy **$5**, and **switch off auto-reload** (it is on by default).
3. **API keys → Create new secret key.** Copy it into `OPENAI_API_KEY`.

> Prepaid cards are usually refused. Use a dual-currency debit/credit card or a freelancer virtual card.

### 1c. Groq: the free brain and ears (needed)
1. Go to **console.groq.com** and sign up (no card needed).
2. **API Keys → Create.** Copy it into `GROQ_API_KEY`.
In free mode Groq does all the thinking and listening. If you later add Claude or OpenAI, Groq becomes their automatic backup.

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

## Step 4 (free). Put him online with Oracle Cloud + DuckDNS

This keeps Mr. Bob running 24/7 for ৳0, so reminders and the night report arrive even when your laptop is off.

### 4.1 Get a free server
1. Sign up at **cloud.oracle.com/free**. Oracle checks your card with a small temporary hold that is given back; **Always Free** resources never cost anything. Choose a **home region near you** that offers Ampere A1 (for example Singapore or Mumbai). You can't change it later.
2. **Compute → Instances → Create instance.**
   - Image: **Canonical Ubuntu 24.04** (the `aarch64` version).
   - Shape: **Ampere → VM.Standard.A1.Flex**, **2 OCPUs, 12 GB memory** (inside the Always Free limit).
   - Add your SSH key (or let Oracle make one and download it).
   - If it says *out of capacity*, try again later or pick another availability domain.
3. Open the web ports: **Instance → Subnet → Security list → Add ingress rules**: source `0.0.0.0/0`, TCP, ports **80** and **443**.
4. Note the instance's **public IP**.

### 4.2 Get a free web address
1. Go to **duckdns.org**, sign in with Google or GitHub.
2. Type a name (for example `jonayedbob`) → **add domain**. Put your server's public IP in **current ip** → **update ip**.
3. Your address is now `jonayedbob.duckdns.org`.

### 4.3 Install and start
```bash
ssh ubuntu@YOUR_IP
# Oracle's Ubuntu blocks web ports inside the server too; open them:
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && newgrp docker

git clone https://github.com/Jonayed100/Mr.Bob-Ai-Agent.git
cd Mr.Bob-Ai-Agent
cp .env.example .env
nano .env        # paste GROQ_API_KEY, Telegram, CallMeBot, Google keys, then set:
                 #   PUBLIC_URL=https://jonayedbob.duckdns.org
                 #   DOMAIN=jonayedbob.duckdns.org
                 #   a strong DASHBOARD_PASSWORD and SECRET_KEY
mkdir -p data && sudo chown -R 1000:1000 data
docker compose up -d --build
```
After a minute open **https://jonayedbob.duckdns.org**. Caddy gets the HTTPS certificate by itself. In Google Cloud, add `https://jonayedbob.duckdns.org/api/google/callback` as a redirect URI.

> No card at all? Run Mr. Bob on your own computer (Step 2). It's free too, but he only works while the computer is on.

## Step 4 (paid). Put him online (server + domain)

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
mkdir -p data && chown -R 1000:1000 data    # Mr. Bob runs as a normal user, so he must own his data folder
docker compose up -d --build
```

What happens:
- `bob` is the app. `caddy` gets a free HTTPS certificate for your domain automatically.
- After a minute, open **https://bob.yourdomain.com** on your phone or laptop.
- Add the server redirect URI from Step 1f if you haven't, then connect Google again from the online dashboard.

Useful commands:
```bash
docker compose ps               # "healthy" means Mr. Bob and his database are fine
curl -s https://bob.yourdomain.com/health      # {"ok": true, "database": "up", ...}
docker compose logs -f bob      # watch what Mr. Bob is doing
docker compose restart bob      # after changing .env
git pull && docker compose up -d --build    # update to the newest code
```

Your data lives in the `data/` folder on the server. Back it up now and then:
```bash
cp data/mrbob.db ~/mrbob-backup-$(date +%F).db
```

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

### The phone app
Mr. Bob has a real app for Android and iPhone in the `mobile/` folder, with push notifications. **See [mobile/README.md](mobile/README.md)**: you can try it on your phone in a few minutes with Expo Go, then build an installable Android app for free.

Quick option without installing anything: open the dashboard in Chrome (Android) or Safari (iPhone) → **Add to Home Screen**.

---

## Monthly cost

**Free mode: ৳0.** The table below is only for the paid upgrade (target ৳2,700).

| Item | About | Paid with |
|---|---|---|
| Server (4 GB VPS) | ৳1,300 | bKash |
| Claude (brain) | ৳600 | USD card, prepaid |
| OpenAI speech-to-text | ৳350 | USD card, prepaid |
| Domain | ৳150 (per month, paid yearly) | bKash |
| 15% VAT on USD payments | ৳140 | added by your bank |
| Natural voice (OpenAI, about $0.015 per spoken minute) | ~৳180 | USD card, prepaid |
| Telegram, WhatsApp alerts, bKash tracking, Groq backup, weather, database | ৳0 | — |

The dashboard's **Monthly cost** card shows real spending: every Claude and speech-to-text call is recorded. Things that keep it low:
- Keyword rules decide most emails without the AI.
- `CLAUDE_MODEL=claude-haiku-4-5` is fast and cheap. Change it in `.env` if you want a bigger model.
- Raise `GMAIL_CHECK_MINUTES` to 15 or 20 to spend less.
- Keep auto-reload off on both AI accounts, so the bill can never go over what you loaded.

---

## Settings you might change

All in `.env` (restart after changing):

- `MORNING_BRIEFING_TIME`, `EVENING_SUMMARY_TIME`: when briefings arrive.
- `TTS_PROVIDER`, `TTS_OPENAI_VOICE`: the natural voice (`ash`, `coral`, `sage`…). Set `TTS_PROVIDER=edge` for free voices only.
- `TTS_VOICE_*`: the free backup voices. Other Bangla voice: `bn-BD-NabanitaNeural`.
- `CITY`, `LATITUDE`, `LONGITUDE`: for weather.
- `STT_MODEL`: if OpenAI retires a speech model, put the new name here.

## Security

- **Strong secrets are required online.** If `PUBLIC_URL` is `https://…` and the password or `SECRET_KEY` is still the sample (or the key is shorter than 32 characters), Mr. Bob refuses to start.
- **Password guessing is blocked.** 5 wrong passwords from one address locks it out for 15 minutes.
- **Changing `DASHBOARD_PASSWORD` logs out every device**, including any you lost.
- **Only you.** Telegram and WhatsApp messages from any other number are ignored; the WhatsApp webhook checks Meta's signature; the SMS webhook needs its token.
- **Safe defaults.** Security headers on every page, no API docs exposed, HTTPS through Caddy, the app runs as a normal (non-root) user, and passwords, OTPs and card numbers are never saved to memory.
- **Never commit `.env`.** It is in `.gitignore`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard says "Can't reach Mr. Bob" | `docker compose logs bob` and look for the error. Usually a typo in `.env`. |
| Google says `redirect_uri_mismatch` | The URI in Google Cloud must exactly equal `PUBLIC_URL` + `/api/google/callback`. |
| Gmail stopped after a week | The Google app is still in Testing mode. Publish it (Step 1f), then reconnect. |
| He can't hear me | The page must be HTTPS (or localhost). Tap the lock icon in the address bar → allow **Microphone**, then tap Bob again. |
| No sound on iPhone | Turn off silent mode. Tap anywhere once after opening the page; phones only allow sound after a tap. |
| Login says "Too many wrong tries" | Wait 15 minutes, or restart Mr. Bob (`docker compose restart bob`). |
| `docker compose ps` shows unhealthy | `docker compose logs bob`. Often the `data/` folder isn't owned by user 1000 (see Step 4c). |
| Telegram silent | Send `/start` and share your number again; check `OWNER_PHONE` and that Telegram is on in Settings. |
| No WhatsApp alerts | Check `CALLMEBOT_APIKEY` and `OWNER_PHONE`; redo the CallMeBot activation message. |
| bKash card empty | Check the forwarder app's URL and token; `docker compose logs bob` shows each `/api/sms` call. |
| Replies say "my brain is offline" | Check `ANTHROPIC_API_KEY` and your Claude credit, and add `GROQ_API_KEY` as a backup. |

## Ideas for later
- Always-on "Hey Bob" on a small device (Raspberry Pi with a custom wake word).
- Nagad and bank SMS tracking.
- Publish the phone app on Google Play and the App Store.

---

Made by **Jonayed Hossain** · Project Aethrix · Dhaka
