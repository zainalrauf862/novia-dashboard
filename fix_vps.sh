#!/usr/bin/env bash
# Update VPS: ambil kode terbaru + pasang auto-update kode + tarik data. Jalankan sebagai root.
cd /opt/novia || { echo "folder /opt/novia tidak ada"; exit 1; }

echo "=== 1) Ambil kode terbaru dari GitHub ==="
git fetch -q origin 2>&1 | tail -1
git reset -q --hard origin/main 2>&1 | tail -1
echo "kode: OK"

echo
echo "=== 2) Pasang auto-update: cron akan ambil kode + data tiap 15 menit ==="
cat > /etc/cron.d/novia <<'CRON'
SHELL=/bin/bash
TZ=Asia/Jakarta
*/15 * * * * root cd /opt/novia && git fetch -q origin && git reset -q --hard origin/main && /usr/bin/python3 pull_novia.py >/opt/novia/pull.log 2>&1 && cp -f /opt/novia/novia-dashboard.html /opt/novia/index.html
CRON
chmod 644 /etc/cron.d/novia
systemctl restart cron
echo "cron: OK (auto ambil kode + data)"

echo
echo "=== 3) Tarik data sekarang ==="
python3 pull_novia.py 2>&1 | tail -20
cp -f novia-dashboard.html index.html 2>/dev/null

echo
echo "=== 4) Hasil ==="
python3 -c "import json;d=json.load(open('data.json'));print('  Campaign hari ini:',len(d.get('campaigns_today',[])),'| kemarin:',len(d.get('campaigns_yesterday',[])));print('  Konten bulan ini:',len(d.get('content_month',[])),'| hari ini:',len(d.get('content_today',[])));print('  Data per:',d.get('generated_at'))" 2>&1

echo
echo "=== SELESAI. Mulai sekarang update kode OTOMATIS tiap 15 menit. ==="
echo "Refresh: https://dash-adszainal.tech"
