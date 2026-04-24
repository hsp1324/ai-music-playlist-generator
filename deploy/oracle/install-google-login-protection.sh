#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-music-playlist-generator}"
HOSTNAME="${AIMP_AUTH_HOSTNAME:-ai-music.168.107.34.175.sslip.io}"
APP_ENV_FILE="${APP_ENV_FILE:-/etc/ai-music-playlist-generator.env}"
OAUTH2_PROXY_CONFIG="${OAUTH2_PROXY_CONFIG:-/etc/oauth2-proxy-ai-music-playlist-generator.cfg}"
OAUTH2_PROXY_EMAILS_FILE="${OAUTH2_PROXY_EMAILS_FILE:-/etc/oauth2-proxy-ai-music-playlist-generator-authenticated-emails.txt}"
OAUTH2_PROXY_SERVICE="oauth2-proxy-ai-music-playlist-generator"
NGINX_SITE="/etc/nginx/sites-available/ai-music-playlist-generator"
PUBLIC_BASE_URL="https://${HOSTNAME}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

if [[ -z "${GOOGLE_CLIENT_ID:-}" || -z "${GOOGLE_CLIENT_SECRET:-}" ]]; then
  echo "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required." >&2
  echo "Create a Google OAuth web client with redirect URI: ${PUBLIC_BASE_URL}/oauth2/callback" >&2
  exit 1
fi

if [[ ! -d "${APP_DIR}" ]]; then
  echo "App directory not found: ${APP_DIR}" >&2
  exit 1
fi

if [[ -z "${OAUTH2_PROXY_COOKIE_SECRET:-}" ]]; then
  OAUTH2_PROXY_COOKIE_SECRET="$(python3 -c 'import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
fi
export OAUTH2_PROXY_COOKIE_SECRET

ALLOWED_EMAIL_DOMAINS="${ALLOWED_EMAIL_DOMAINS:-*}"
ALLOWED_EMAILS="${ALLOWED_EMAILS:-}"
OAUTH2_PROXY_VERSION="${OAUTH2_PROXY_VERSION:-}"

apt-get update
apt-get install -y certbot python3-certbot-nginx curl tar

install -m 0644 "${APP_DIR}/deploy/oracle/nginx-ai-music-playlist-generator.conf" "${NGINX_SITE}"
sed -i "s/YOUR_DOMAIN_OR_IP/${HOSTNAME}/g" "${NGINX_SITE}"
nginx -t
systemctl reload nginx

if ! command -v oauth2-proxy >/dev/null 2>&1; then
  arch="$(uname -m)"
  case "${arch}" in
    x86_64) oauth_arch="amd64" ;;
    aarch64|arm64) oauth_arch="arm64" ;;
    *)
      echo "Unsupported architecture for automatic oauth2-proxy install: ${arch}" >&2
      exit 1
      ;;
  esac

  if [[ -z "${OAUTH2_PROXY_VERSION}" ]]; then
    OAUTH2_PROXY_VERSION="$(curl -fsSL https://api.github.com/repos/oauth2-proxy/oauth2-proxy/releases/latest | sed -n 's/.*"tag_name": "\(v[^"]*\)".*/\1/p' | head -n 1)"
  fi

  if [[ -z "${OAUTH2_PROXY_VERSION}" ]]; then
    echo "Could not determine latest oauth2-proxy version." >&2
    exit 1
  fi

  version_no_v="${OAUTH2_PROXY_VERSION#v}"
  archive="oauth2-proxy-${version_no_v}.linux-${oauth_arch}.tar.gz"
  url="https://github.com/oauth2-proxy/oauth2-proxy/releases/download/${OAUTH2_PROXY_VERSION}/${archive}"
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' EXIT

  curl -fsSL "${url}" -o "${tmpdir}/${archive}"
  tar -xzf "${tmpdir}/${archive}" -C "${tmpdir}"
  install -m 0755 "${tmpdir}/oauth2-proxy-${version_no_v}.linux-${oauth_arch}/oauth2-proxy" /usr/local/bin/oauth2-proxy
fi

certbot --nginx -d "${HOSTNAME}" --non-interactive --agree-tos --register-unsafely-without-email

install -m 0644 "${APP_DIR}/deploy/oracle/oauth2-proxy-ai-music-playlist-generator.service" "/etc/systemd/system/${OAUTH2_PROXY_SERVICE}.service"
install -m 0600 "${APP_DIR}/deploy/oracle/oauth2-proxy-ai-music-playlist-generator.cfg" "${OAUTH2_PROXY_CONFIG}"

python3 - "$OAUTH2_PROXY_CONFIG" "$HOSTNAME" "$ALLOWED_EMAIL_DOMAINS" "$ALLOWED_EMAILS" "$OAUTH2_PROXY_EMAILS_FILE" <<'PY'
from pathlib import Path
import os
import sys

config_path, hostname, domains, emails, emails_file = sys.argv[1:]
client_id = os.environ["GOOGLE_CLIENT_ID"]
client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
cookie_secret = os.environ["OAUTH2_PROXY_COOKIE_SECRET"]
path = Path(config_path)
text = path.read_text()

domain_items = ", ".join(f'"{item.strip()}"' for item in domains.split(",") if item.strip())
if not domain_items:
    domain_items = '"*"'

replacements = {
    'client_id = "REPLACE_WITH_GOOGLE_OAUTH_CLIENT_ID"': f'client_id = "{client_id}"',
    'client_secret = "REPLACE_WITH_GOOGLE_OAUTH_CLIENT_SECRET"': f'client_secret = "{client_secret}"',
    'cookie_secret = "REPLACE_WITH_BASE64_COOKIE_SECRET"': f'cookie_secret = "{cookie_secret}"',
    'redirect_url = "https://ai-music.168.107.34.175.sslip.io/oauth2/callback"': f'redirect_url = "https://{hostname}/oauth2/callback"',
    'email_domains = ["*"]': f'email_domains = [{domain_items}]',
    '"ai-music.168.107.34.175.sslip.io"': f'"{hostname}"',
}

for source, target in replacements.items():
    text = text.replace(source, target)

email_items = [item.strip() for item in emails.split(",") if item.strip()]
if email_items:
    text = text.rstrip() + f'\nauthenticated_emails_file = "{emails_file}"\n'

path.write_text(text)
PY

if [[ -n "${ALLOWED_EMAILS}" ]]; then
  printf '%s\n' "${ALLOWED_EMAILS}" | tr ',' '\n' | sed '/^[[:space:]]*$/d' >"${OAUTH2_PROXY_EMAILS_FILE}"
  chmod 600 "${OAUTH2_PROXY_EMAILS_FILE}"
fi

install -m 0644 "${APP_DIR}/deploy/oracle/nginx-ai-music-playlist-generator-protected.conf" "${NGINX_SITE}"
sed -i "s/ai-music\.168\.107\.34\.175\.sslip\.io/${HOSTNAME}/g" "${NGINX_SITE}"

if grep -q '^AIMP_PUBLIC_BASE_URL=' "${APP_ENV_FILE}"; then
  sed -i "s#^AIMP_PUBLIC_BASE_URL=.*#AIMP_PUBLIC_BASE_URL=${PUBLIC_BASE_URL}#" "${APP_ENV_FILE}"
else
  printf '\nAIMP_PUBLIC_BASE_URL=%s\n' "${PUBLIC_BASE_URL}" >>"${APP_ENV_FILE}"
fi

systemctl daemon-reload
systemctl enable --now "${OAUTH2_PROXY_SERVICE}"
systemctl restart ai-music-playlist-generator
nginx -t
systemctl reload nginx

echo "Google login protection is installed for ${PUBLIC_BASE_URL}"
echo "Google OAuth redirect URI: ${PUBLIC_BASE_URL}/oauth2/callback"
