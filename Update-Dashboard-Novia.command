#!/bin/bash
# Dobel-klik file ini untuk memperbarui data dashboard Novia.
cd "$(dirname "$0")"
echo "=============================================="
echo "   Memperbarui Dashboard Novia dari Meta Ads"
echo "=============================================="
python3 pull_novia.py
echo ""
echo "Selesai. Tekan Enter untuk menutup jendela ini..."
read _
