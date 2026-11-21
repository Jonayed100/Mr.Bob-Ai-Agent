# Changelog

## 2.3.0
- Deploy on Render (free) with one Blueprint (`render.yaml`); works entirely from a phone.
- Postgres support (Supabase, Neon or Render links work as given) so data survives restarts on free hosts.
- Public address fills itself in on Render; optional keep-awake so reminders keep working.
- Docker image honours `$PORT`.
- One-command installer (`install.sh`) for your own server.

## 2.2.0
- Free mode (৳0 a month): Groq's free model is now a full brain with every tool (reminders, memory, Gmail, calendar), not just a backup.
- Background jobs use a smaller free model so chatting keeps its own quota; short waits and a friendly message when the free limit is reached.
- `.env.example` is set up for free mode by default; Claude and OpenAI are optional upgrades.
- Free 24/7 hosting guide: Oracle Cloud Always Free + DuckDNS.
- Cost card shows "Free mode: ৳0".

## 2.1.0
- Tap Bob's photo to talk; he listens and answers out loud.
- Voice works on phones: sound is unlocked on the first tap, and the browser's voice reads the reply if the server voice can't play.
- Clear help when the microphone is blocked.
- Login lockout after 5 wrong passwords; changing the password logs out every device.
- Refuses to go online with sample secrets.
- Security headers, friendly error responses, and a health check that also tests the database.
- Docker image runs as a non-root user with a built-in health check; log rotation.
- GitHub Actions: lint, tests, JavaScript check and Docker build on every push.

## 2.0.0
- Reminders with date, time, repeat, notes and importance; alerts on the website, Telegram, WhatsApp and phone.
- Night report, part by part, saved to Reports.
- Memory: learns from conversations; view and edit on the Memory page.
- Natural OpenAI voice; replies in English or Bangla to match how you speak.

## 1.0.0
- First version: Gmail, Calendar, weather, bKash tracking, Telegram, dashboard and voice chat.
