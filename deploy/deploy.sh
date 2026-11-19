#!/usr/bin/env bash
# First deploy (and manual redeploys) of the copilot onto the shared server.
# Pulls main, builds and starts the container, registers its unlisted route with Caddy, and
# installs the timer that auto-deploys later commits once CI passes (autodeploy.sh).
# Usage: deploy/deploy.sh            (reads deploy/deploy.env)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$here/deploy.env" ]]; then
  # shellcheck disable=SC1091
  source "$here/deploy.env"
fi
: "${DEPLOY_HOST:?set DEPLOY_HOST (see deploy/deploy.env.example)}"
: "${APP_HOST:?set APP_HOST}"

# The unlisted path: generated once, then reused so a shared link keeps working.
if [[ -z "${COPILOT_PATH:-}" ]]; then
  COPILOT_PATH="$(openssl rand -hex 12)"
  if [[ -f "$here/deploy.env" ]]; then
    sed -i.bak "s/^COPILOT_PATH=.*/COPILOT_PATH=$COPILOT_PATH/" "$here/deploy.env" && rm -f "$here/deploy.env.bak"
  fi
  echo "Generated COPILOT_PATH (saved to deploy/deploy.env)."
fi
[[ "$COPILOT_PATH" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "COPILOT_PATH must be URL-safe" >&2; exit 1; }

repo_url="$(git -C "$here/.." remote get-url origin)"

ssh -o StrictHostKeyChecking=accept-new "ubuntu@$DEPLOY_HOST" bash -s <<REMOTE
set -euo pipefail
sudo install -d -o ubuntu -g ubuntu /srv/copilot
[[ -d /srv/copilot/.git ]] || git clone -q '$repo_url' /srv/copilot
cd /srv/copilot
git fetch -q origin main
git reset -q --hard origin/main
umask 077
echo 'STREAMLIT_SERVER_BASE_URL_PATH=$COPILOT_PATH' > deploy/path.env
touch deploy/.env   # OPENAI_API_KEY goes here; created empty once, never overwritten
docker compose -f deploy/compose.yml up -d --build --remove-orphans
docker image prune -f >/dev/null
# Streamlit already serves under /COPILOT_PATH/ (base URL path), so Caddy passes the path through.
sudo install -d -o ubuntu -g ubuntu /srv/caddy-sites
cat > /srv/caddy-sites/copilot.caddy <<CADDY
redir /$COPILOT_PATH /$COPILOT_PATH/ 308
handle /$COPILOT_PATH/* {
	reverse_proxy copilot:8501
}
CADDY
docker exec \$(docker ps -q --filter label=com.docker.compose.project=market-calibration --filter label=com.docker.compose.service=caddy) caddy reload --config /etc/caddy/Caddyfile
sudo install -m 644 deploy/systemd/copilot-deploy.service deploy/systemd/copilot-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now copilot-deploy.timer >/dev/null
REMOTE

echo "Live at: https://$APP_HOST/$COPILOT_PATH/"
