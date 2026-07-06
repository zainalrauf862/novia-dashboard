#!/usr/bin/env bash
# Diagnosa + perbaiki data konten di VPS.
cd /opt/novia || { echo "folder /opt/novia tidak ada"; exit 1; }

echo "=== 1) Pastikan kode terbaru dari GitHub ==="
git fetch -q origin 2>&1 | tail -1
git reset -q --hard origin/main 2>&1 | tail -1
echo "kode: OK"

echo
echo "=== 2) Tarik data sekarang (tampilkan error kalau ada) ==="
python3 pull_novia.py 2>&1 | tail -25
cp -f novia-dashboard.html index.html 2>/dev/null

echo
echo "=== 3) Hasil KONTEN di data.json ==="
python3 -c "import json;d=json.load(open('data.json'));print('  bulan ini :',len(d.get('content_month',[])),'konten');print('  hari ini  :',len(d.get('content_today',[])),'konten');print('  data per  :',d.get('generated_at'))" 2>&1

echo
echo "=== 4) Status cron (harus active) ==="
systemctl is-active cron
grep -o 'pull_novia.py' /etc/cron.d/novia 2>/dev/null && echo "  jadwal cron: ADA" || echo "  jadwal cron: TIDAK ADA"

echo
echo "=== 5) Log pull terakhir ==="
tail -6 /opt/novia/pull.log 2>/dev/null || echo "  (belum ada log)"
echo
echo "=== SELESAI. Sekarang refresh https://dash-adszainal.tech ==="
