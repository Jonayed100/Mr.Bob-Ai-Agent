#!/usr/bin/env bash
# Mr. Bob one-command installer for a fresh Ubuntu server (for example Oracle Cloud Always Free).
#
#   bash install.sh
#
# It asks a few questions, then: installs Docker, opens the web ports,
# writes .env (with a random secret key), and starts Mr. Bob with HTTPS.
# Safe to run again: it keeps your existing .env unless you choose to replace it.
set -euo pipefail

cd "$(dirname "$0")"
say()  { printf '\n\033[1;31m▸ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
ask()  { local v; read -rp "  $1: " v; printf '%s' "$v"; }
asks() { local v; read -rsp "  $1: " v; echo >&2; printf '%s' "$v"; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

say "1/5  Installing Docker (skipped if already there)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | $SUDO sh
fi
ok "Docker ready"

say "2/5  Opening web ports 80 and 443 on this server"
if command -v iptables >/dev/null 2>&1; then
  for port in 80 443; do
    $SUDO iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
      || $SUDO iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
  done
  if ! command -v netfilter-persistent >/dev/null 2>&1; then
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | $SUDO debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean true | $SUDO debconf-set-selections
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null
  fi
  $SUDO netfilter-persistent save >/dev/null 2>&1 || true
fi
ok "Ports open (also add ports 80 and 443 in your cloud's firewall / security list)"

say "3/5  Your settings"
write_env=yes
if [ -f .env ]; then
  keep=$(ask "A .env already exists. Keep it? (Y/n)")
  case "${keep:-y}" in [nN]*) write_env=yes ;; *) write_env=no ;; esac
fi

if [ "$write_env" = yes ]; then
  echo "  Press Enter to skip anything optional. You can change it later in .env"
  DOMAIN=$(ask "Your web address, e.g. jonayedbob.duckdns.org")
  DOMAIN=${DOMAIN#https://}; DOMAIN=${DOMAIN#http://}; DOMAIN=${DOMAIN%/}
  PASSWORD=""
  while [ ${#PASSWORD} -lt 8 ]; do
    PASSWORD=$(asks "Dashboard password (8+ characters, hidden)")
    [ ${#PASSWORD} -lt 8 ] && echo "  Too short, try again."
  done
  GROQ=$(asks "Groq API key (free, from console.groq.com)")
  TELEGRAM=$(asks "Telegram bot token from @BotFather (optional)")
  CALLMEBOT=$(asks "CallMeBot WhatsApp API key (optional)")
  GOOGLE_ID=$(ask "Google OAuth Client ID (optional)")
  GOOGLE_SECRET=$(asks "Google OAuth Client secret (optional)")
  SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')

  cp .env.example .env
  chmod 600 .env
  DOMAIN="$DOMAIN" PASSWORD="$PASSWORD" GROQ="$GROQ" TELEGRAM="$TELEGRAM" CALLMEBOT="$CALLMEBOT" \
  GOOGLE_ID="$GOOGLE_ID" GOOGLE_SECRET="$GOOGLE_SECRET" SECRET="$SECRET" python3 - <<'PY'
import os, re
values = {
    "PUBLIC_URL": f"https://{os.environ['DOMAIN']}",
    "DOMAIN": os.environ["DOMAIN"],
    "DASHBOARD_PASSWORD": os.environ["PASSWORD"],
    "SECRET_KEY": os.environ["SECRET"],
    "GROQ_API_KEY": os.environ["GROQ"],
    "TELEGRAM_BOT_TOKEN": os.environ["TELEGRAM"],
    "CALLMEBOT_APIKEY": os.environ["CALLMEBOT"],
    "GOOGLE_CLIENT_ID": os.environ["GOOGLE_ID"],
    "GOOGLE_CLIENT_SECRET": os.environ["GOOGLE_SECRET"],
}
text = open(".env").read()
for key, value in values.items():
    text = re.sub(rf"(?m)^{key}=.*$", lambda m: f"{key}={value}", text)
open(".env", "w").write(text)
PY
  ok "Settings saved to .env"
else
  DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2-)
  ok "Keeping your existing .env"
fi

say "4/5  Starting Mr. Bob (the first build takes a few minutes)"
mkdir -p data caddy_data caddy_config
$SUDO chown -R 1000:1000 data
$SUDO docker compose up -d --build

say "5/5  Checking he is healthy"
for _ in $(seq 1 40); do
  state=$($SUDO docker inspect -f '{{.State.Health.Status}}' "$($SUDO docker compose ps -q bob)" 2>/dev/null || echo starting)
  [ "$state" = healthy ] && break
  sleep 3
done
if [ "${state:-}" = healthy ]; then
  ok "Mr. Bob is awake!"
  echo
  echo "  Open on your phone:  https://${DOMAIN}"
  echo "  (HTTPS can take a minute the very first time.)"
  echo "  iPhone: Safari → Share → Add to Home Screen"
  echo "  Telegram: open your bot, send /start, tap 'Share my number'"
  [ -n "${GOOGLE_ID:-}" ] && echo "  Google: add https://${DOMAIN}/api/google/callback as a redirect URI, then Settings → Connect"
else
  echo "  He's taking longer than usual. See what he says with:"
  echo "    sudo docker compose logs --tail 50 bob"
fi
