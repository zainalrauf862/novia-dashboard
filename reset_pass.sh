#!/usr/bin/env bash
# Reset login (username & password) Dashboard Novia. Jalankan sebagai root di VPS.
set -e
echo "=================================================="
echo "     RESET LOGIN DASHBOARD NOVIA"
echo "=================================================="
echo ">> Buat USERNAME baru (contoh: admin):"
read -r DASH_USER
echo ">> Buat PASSWORD baru:"
read -r DASH_PASS
htpasswd -bc /etc/nginx/.novia_htpasswd "$DASH_USER" "$DASH_PASS" >/dev/null 2>&1
nginx -t && systemctl reload nginx
echo
echo "=================================================="
echo "  ✅ LOGIN DIPERBARUI"
echo "  Buka: https://dash-adszainal.tech"
echo "  User: $DASH_USER"
echo "=================================================="
