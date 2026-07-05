#!/usr/bin/env bash
# Pasang domain + HTTPS (Let's Encrypt) untuk Dashboard Novia. Jalankan sebagai root.
set -e
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
DOMAIN="dash-adszainal.tech"

echo "=================================================="
echo "     PASANG DOMAIN + HTTPS: $DOMAIN"
echo "=================================================="

# 1. Set nama domain di konfigurasi nginx
echo "[1/3] Menyetel nama domain di web server ..."
cat > /etc/nginx/sites-available/novia <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    root /opt/novia;
    index index.html;
    location / {
        auth_basic "Dashboard Novia";
        auth_basic_user_file /etc/nginx/.novia_htpasswd;
        add_header Cache-Control "no-store, must-revalidate";
        try_files \$uri \$uri/ =404;
    }
}
NGINX
nginx -t && systemctl reload nginx

# 2. Pasang certbot
echo "[2/3] Memasang certbot ..."
apt-get update -y -qq
apt-get install -y -qq certbot python3-certbot-nginx

# 3. Ambil sertifikat SSL + aktifkan HTTPS + redirect otomatis
echo "[3/3] Mengambil sertifikat HTTPS ..."
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
        --non-interactive --agree-tos --redirect \
        --register-unsafely-without-email

echo
echo "=================================================="
echo "  SELESAI! Dashboard sekarang:"
echo "  https://$DOMAIN"
echo "  (login user/password sama seperti sebelumnya)"
echo "=================================================="
