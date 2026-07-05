#!/usr/bin/env bash
# Setup Dashboard Novia di VPS Ubuntu. Jalankan sebagai root.
set -e
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a

echo "=================================================="
echo "     SETUP DASHBOARD NOVIA DI VPS"
echo "=================================================="

# --- 1. Zona waktu WIB ---
timedatectl set-timezone Asia/Jakarta 2>/dev/null || true

# --- 2. Pasang paket ---
echo "[1/6] Memasang nginx, python3, git ..."
apt-get update -y -qq
apt-get install -y -qq nginx python3 git apache2-utils curl

# --- 3. Ambil file dashboard dari GitHub ---
echo "[2/6] Mengunduh file dashboard ..."
rm -rf /opt/novia
git clone -q https://github.com/zainalrauf862/novia-dashboard.git /opt/novia

# --- 4. Token Meta ---
echo
echo "-------------------------------------------------"
echo ">> TEMPEL ACCESS TOKEN META kamu di bawah ini, lalu tekan ENTER:"
read -r META_TOKEN
echo "$META_TOKEN" > /opt/novia/token.txt
chmod 600 /opt/novia/token.txt

# --- 5. Username & password untuk buka dashboard ---
echo
echo ">> Buat USERNAME untuk login dashboard (contoh: admin):"
read -r DASH_USER
echo ">> Buat PASSWORD untuk login dashboard:"
read -r DASH_PASS
htpasswd -bc /etc/nginx/.novia_htpasswd "$DASH_USER" "$DASH_PASS" >/dev/null 2>&1

# --- 6. Tarik data pertama ---
echo
echo "[3/6] Menarik data Meta pertama kali ..."
cd /opt/novia
python3 pull_novia.py || echo "  (peringatan: cek token bila gagal)"
cp -f novia-dashboard.html index.html

# --- 7. Konfigurasi nginx (dengan password, tanpa cache) ---
echo "[4/6] Menyetel web server ..."
cat > /etc/nginx/sites-available/novia <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root /opt/novia;
    index index.html;
    location / {
        auth_basic "Dashboard Novia";
        auth_basic_user_file /etc/nginx/.novia_htpasswd;
        add_header Cache-Control "no-store, must-revalidate";
        try_files $uri $uri/ =404;
    }
}
NGINX
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/novia /etc/nginx/sites-enabled/novia
nginx -t && systemctl restart nginx && systemctl enable nginx >/dev/null 2>&1

# --- 8. Jadwal update tiap 10 menit (cron) ---
echo "[5/6] Menyetel update otomatis tiap 10 menit ..."
cat > /etc/cron.d/novia <<'CRON'
SHELL=/bin/bash
TZ=Asia/Jakarta
*/10 * * * * root cd /opt/novia && /usr/bin/python3 pull_novia.py >/opt/novia/pull.log 2>&1 && cp -f /opt/novia/novia-dashboard.html /opt/novia/index.html
CRON
chmod 644 /etc/cron.d/novia
systemctl restart cron

# --- 9. Selesai ---
echo "[6/6] Selesai!"
IP=$(curl -s --max-time 8 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo
echo "=================================================="
echo "  DASHBOARD SIAP!"
echo "  Buka di browser:  http://$IP"
echo "  Login user     :  $DASH_USER"
echo "  Update otomatis :  tiap 10 menit"
echo "=================================================="
