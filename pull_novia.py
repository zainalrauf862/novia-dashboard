#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Penarik data Meta Ads untuk dashboard Novia.
Cara pakai:
  1. Buat file 'token.txt' di folder yang sama, isi dengan access token kamu (satu baris).
  2. Jalankan:  python3 pull_novia.py
  3. Buka 'novia-dashboard.html' — datanya sudah diperbarui.

Skrip ini HANYA MEMBACA data (pakai izin ads_read). Tidak mengubah iklan apa pun.
Token disimpan di token.txt (terpisah), TIDAK ditulis ke file HTML.
"""
import json, os, re, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta

AD_ACCOUNT = "1630362674392137"          # diisi otomatis per akun oleh loop (lihat __main__)
ACCOUNTS = [                             # daftar akun yg tampil di dashboard — tambah/ubah di sini
    {"id": "1630362674392137", "name": "Novia"},
    {"id": "1475202733411240", "name": "SVO ZR-11"},
]
PIXEL      = "875398195344375"           # Pixel "Produk Novia Kewanitaan" (tidak dipakai lagi)
API_VER    = "v21.0"
BASE       = f"https://graph.facebook.com/{API_VER}"
HERE       = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(HERE, "novia-dashboard.html")
DATA_JSON  = os.path.join(HERE, "data.json")
def heavy_path():   # cache data berat per-akun (demografi/mingguan/wilayah)
    return os.path.join(HERE, f".heavy_cache_{AD_ACCOUNT}.json")

def load_heavy():
    try:
        return json.load(open(heavy_path(), encoding="utf-8"))
    except Exception:
        return {}

BULAN = {"01":"Januari","02":"Februari","03":"Maret","04":"April","05":"Mei","06":"Juni",
         "07":"Juli","08":"Agustus","09":"September","10":"Oktober","11":"November","12":"Desember"}

# ---------- token ----------
def load_token():
    tok = os.environ.get("META_TOKEN", "").strip()   # dipakai di GitHub Actions (secret)
    if tok:
        return tok
    p = os.path.join(HERE, "token.txt")               # dipakai di komputer lokal
    if not os.path.exists(p):
        sys.exit("❌ Token tidak ada (set env META_TOKEN, atau buat file token.txt).")
    tok = open(p, encoding="utf-8").read().strip()
    if not tok:
        sys.exit("❌ token.txt kosong. Tempel token kamu di dalamnya.")
    return tok

TOKEN = load_token()

# ---------- API helper ----------
def api(path, **params):
    params["access_token"] = TOKEN
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"❌ Meta menolak permintaan (HTTP {e.code}).\n   {body}\n"
                           "   Kemungkinan: token salah/kadaluarsa, atau izin/akun iklan belum tersambung.")

def api_all(path, **params):
    """Ambil SEMUA data (ikuti halaman berikutnya) — tanpa batas jumlah."""
    res = api(path, **params)
    out = list(res.get("data", []))
    guard = 0
    while res.get("paging", {}).get("next") and guard < 50:
        guard += 1
        with urllib.request.urlopen(res["paging"]["next"], timeout=90) as r:
            res = json.load(r)
        out += res.get("data", [])
    return out

def insights(**params):
    """Ambil semua baris insights (ikuti halaman berikutnya bila ada)."""
    rows, res = [], api(f"act_{AD_ACCOUNT}/insights", **params)
    rows += res.get("data", [])
    # pagination (untuk breakdown yang banyak baris)
    guard = 0
    while res.get("paging", {}).get("next") and guard < 20:
        guard += 1
        with urllib.request.urlopen(res["paging"]["next"], timeout=90) as r:
            res = json.load(r)
        rows += res.get("data", [])
    return rows

# ---------- parsing ----------
def f(row, key, default=0.0):
    try: return float(str(row.get(key, default)).replace(",", ""))
    except (TypeError, ValueError): return default

def i(row, key, default=0):
    return int(round(f(row, key, default)))

def action(row, *types):
    """Ambil nilai dari array 'actions'/'*_watched_actions' berdasarkan action_type."""
    for t in types:
        for a in (row.get("actions") or []):
            if a.get("action_type") == t:
                return int(round(float(a.get("value", 0))))
    return 0

def action_list(row, key, *types):
    for t in types:
        for a in (row.get(key) or []):
            if a.get("action_type") == t:
                return float(a.get("value", 0))
    # kalau tak spesifik, ambil elemen pertama
    lst = row.get(key) or []
    return float(lst[0]["value"]) if lst else 0.0

def links(row):   return i(row, "inline_link_clicks") or action(row, "link_click")
def purch(row):   return action(row, "omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")
def roas(row):    return round(action_list(row, "purchase_roas", "omni_purchase", "purchase"), 2)
def purval(row):
    # nilai purchase (value) dari Meta = action_values omni_purchase
    for a in (row.get("action_values") or []):
        if a.get("action_type") in ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase"):
            return int(round(float(a.get("value", 0))))
    return 0

CORE = "spend,impressions,reach,clicks,ctr,cpc,cpm,frequency,inline_link_clicks,actions,purchase_roas,action_values"

def viewlp(r): return action(r, "landing_page_view", "omni_landing_page_view")
def klikwa(r): return action(r, "add_to_cart", "offsite_conversion.fb_pixel_add_to_cart", "onsite_web_add_to_cart")
def contact(r):
    # Event Contact Novia tercatat sebagai fb_pixel_custom (cocok dgn cost per contact_website di Ads Manager)
    return action(r, "contact", "contact_total", "offsite_conversion.fb_pixel_contact",
                  "offsite_conversion.fb_pixel_custom")

def core_row(r):
    return {"spend":i(r,"spend"),"impr":i(r,"impressions"),"reach":i(r,"reach"),
            "clicks":i(r,"clicks"),"ctr":round(f(r,"ctr"),2),"cpc":i(r,"cpc"),
            "cpm":i(r,"cpm"),"freq":round(f(r,"frequency"),2),
            "link":links(r),"viewlp":viewlp(r),"klikwa":klikwa(r),
            "contact":contact(r),"purch":purch(r),"roas":roas(r),"purval":purval(r)}

def brk(field, val_key="impressions", preset="last_30d"):
    try:
        rows = insights(level="account", date_preset=preset, breakdowns=field, fields=val_key)
    except Exception as e:
        print(f"  ⚠ lewati breakdown {field} ({e})")
        return []
    out = [[str(r.get(field,"?")), i(r, val_key)] for r in rows if i(r, val_key) > 0]
    out.sort(key=lambda x: -x[1])
    return out

# ---------- bangun DATA ----------
def build():
    heavy_cache = load_heavy()
    now_ts = int(datetime.now().timestamp())
    # tarik data berat (demografi/mingguan/wilayah) sekali per ~jam saja; sisanya pakai cache
    do_heavy = (now_ts - heavy_cache.get("_ts", 0) > 55 * 60) or ("aud_30d" not in heavy_cache)

    print("• menarik ringkasan hari ini & kemarin ...")
    today = insights(level="account", date_preset="today", fields=CORE)
    yday  = insights(level="account", date_preset="yesterday", fields=CORE)
    d = {
        "generated_at": datetime.now().strftime("%d %b %Y %H:%M"),
        "window": f"{(datetime.now()-timedelta(days=29)).strftime('%d %b')} – {datetime.now().strftime('%d %b %Y')}",
        "today":     core_row(today[0]) if today else core_row({}),
        "yesterday": core_row(yday[0])  if yday  else core_row({}),
    }

    print("• menarik campaign hari ini & kemarin (+ status) ...")
    CMET = "{spend,impressions,clicks,ctr,cpc,inline_link_clicks,actions,purchase_roas}"
    cres = api_all(f"act_{AD_ACCOUNT}/campaigns", effective_status='["ACTIVE","PAUSED"]', limit=200,
               fields=f"name,effective_status,insights.date_preset(today).as(hri){CMET},"
                      f"insights.date_preset(yesterday).as(kmr){CMET}")
    def build_camps(key, today_mode):
        rows = []
        for c in cres:
            arr = (c.get(key, {}) or {}).get("data") or []
            ins = arr[0] if arr else {}
            sp = i(ins, "spend")
            off = c.get("effective_status") != "ACTIVE"
            if today_mode:
                if sp <= 0 and off:        # hari ini: sembunyikan hanya (mati & tanpa spend)
                    continue
            else:
                if sp <= 0:                # kemarin: hanya yang benar-benar spend kemarin
                    continue
            rows.append({"name": c.get("name", "?") + (" (Off)" if off else ""), "off": off,
                         "spend": sp, "impr": i(ins, "impressions"), "clicks": i(ins, "clicks"),
                         "ctr": round(f(ins, "ctr"), 2), "cpc": i(ins, "cpc"), "link": links(ins),
                         "viewlp": viewlp(ins), "klikwa": klikwa(ins), "contact": contact(ins),
                         "purch": purch(ins), "roas": roas(ins)})
        rows.sort(key=lambda r: -r["spend"])
        return rows          # tampilkan semua (tanpa batas 25)
    d["campaigns_today"]     = build_camps("hri", True)
    d["campaigns_yesterday"] = build_camps("kmr", False)

    print("• menarik funnel 30 hari ...")
    fn = insights(level="account", date_preset="last_30d", fields=CORE)
    fr = fn[0] if fn else {}
    d["funnel"] = {"spend":i(fr,"spend"),"impressions":i(fr,"impressions"),"reach":i(fr,"reach"),
                   "clicks":i(fr,"clicks"),"link_clicks":links(fr),"viewlp":viewlp(fr),
                   "klikwa":klikwa(fr),"contact":contact(fr),"purchases":purch(fr),
                   "ctr":round(f(fr,"ctr"),2),"cpc":i(fr,"cpc"),"cpm":i(fr,"cpm"),
                   "frequency":round(f(fr,"frequency"),2),"roas":roas(fr),"purval":purval(fr)}

    print("• menarik konten bulan ini & hari ini ...")
    METR = "{spend,impressions,ctr,inline_link_clicks,actions,purchase_roas,video_thruplay_watched_actions}"
    try:
        adlist = api_all(f"act_{AD_ACCOUNT}/ads", effective_status='["ACTIVE","PAUSED","CAMPAIGN_PAUSED","ADSET_PAUSED"]', limit=200,
                   fields="name,effective_status,"
                          f"insights.date_preset(this_month).as(bln){METR},"
                          f"insights.date_preset(today).as(hri){METR}")
    except Exception as e:
        print(f"  ⚠ lewati konten ({e})"); adlist = []

    def content_item(a, ins, off):
        impr = i(ins, "impressions")
        plays = action(ins, "video_view")            # penonton 3 detik = hook rate
        thru  = i2(ins, "video_thruplay_watched_actions")
        return {"nm": a.get("name", "?") + (" (Off)" if off else ""), "off": off,
                "spend": i(ins, "spend"), "impr": impr, "ctr": round(f(ins, "ctr"), 2),
                "link": links(ins), "viewlp": viewlp(ins), "klikwa": klikwa(ins),
                "contact": contact(ins), "purch": purch(ins), "roas": roas(ins),
                "hook": round(plays / impr * 100, 1) if impr else 0,
                "hold": round(thru / plays * 100, 1) if plays else 0}

    month_list, today_list = [], []
    for a in adlist:
        off = a.get("effective_status") != "ACTIVE"
        ins_b = ((a.get("bln", {}) or {}).get("data") or [{}])[0]
        ins_h = ((a.get("hri", {}) or {}).get("data") or [{}])[0]
        if i(ins_b, "spend") > 0 or not off:      # tampil jika aktif ATAU ada spend
            month_list.append(content_item(a, ins_b, off))
        if i(ins_h, "spend") > 0 or not off:
            today_list.append(content_item(a, ins_h, off))
    month_list.sort(key=lambda r: -r["spend"]); today_list.sort(key=lambda r: -r["spend"])
    d["content_month"] = month_list              # tampilkan semua (tanpa batas 30)
    d["content_today"] = today_list
    d["content"] = d["content_month"]             # kompatibilitas lama

    # ===== DATA BERAT (tren, mingguan/bulanan, demografi, wilayah) =====
    # Ini jarang berubah, jadi ditarik sekali per ~jam saja biar hemat permintaan ke Meta.
    HKEYS = ["trend","weekly","monthly","aud_today","aud_yesterday","aud_30d","region_month","region_today"]
    if do_heavy:
        print("• [per jam] menarik tren, mingguan/bulanan, demografi, wilayah ...")
        tr = insights(level="account", date_preset="last_14d", time_increment="1",
                      fields="spend,inline_link_clicks,actions")
        d["trend"] = [[r.get("date_start","")[5:], i(r,"spend"), links(r), purch(r)] for r in tr]

        wk = insights(level="account", date_preset="last_30d", time_increment="7",
                      fields="spend,clicks,inline_link_clicks,actions,purchase_roas")
        d["weekly"] = [[f"{r.get('date_start','')[5:]}→{r.get('date_stop','')[5:]}", i(r,"spend"),
                        i(r,"clicks"), links(r), purch(r), roas(r)] for r in wk]
        mo = insights(level="account", date_preset="last_90d", time_increment="monthly",
                      fields="spend,clicks,inline_link_clicks,actions,purchase_roas")
        d["monthly"] = [[BULAN.get(r.get('date_start','')[5:7], r.get('date_start','')), i(r,"spend"),
                         i(r,"clicks"), links(r), purch(r), roas(r)] for r in mo]

        PLAT = {"facebook":"Facebook","instagram":"Instagram","audience_network":"Audience Network",
                "messenger":"Messenger","unknown":"Lainnya"}
        GEN  = {"female":"Perempuan","male":"Laki-laki","unknown":"Tidak diketahui"}
        REG  = {"West Java":"Jawa Barat","East Java":"Jawa Timur","Central Java":"Jawa Tengah",
                "North Sumatra":"Sumatera Utara","West Sumatra":"Sumatera Barat","South Sumatra":"Sumatera Selatan",
                "East Nusa Tenggara":"NTT","West Nusa Tenggara":"NTB","West Papua":"Papua Barat",
                "North Maluku":"Maluku Utara","South Sulawesi":"Sulawesi Selatan","North Sulawesi":"Sulawesi Utara",
                "Central Sulawesi":"Sulawesi Tengah","Southeast Sulawesi":"Sulawesi Tenggara","West Sulawesi":"Sulawesi Barat",
                "West Kalimantan":"Kalimantan Barat","East Kalimantan":"Kalimantan Timur","South Kalimantan":"Kalimantan Selatan",
                "Central Kalimantan":"Kalimantan Tengah","North Kalimantan":"Kalimantan Utara",
                "Special Region of Yogyakarta":"DI Yogyakarta","Riau Islands":"Kepulauan Riau",
                "Bangka Belitung Islands":"Bangka Belitung"}
        def regnm(s):
            s = s.replace(" (province)", "").strip()
            return REG.get(s, s)
        def audience(preset):
            return {"age":       brk("age", "impressions", preset),
                    "gender":    [[GEN.get(g,g.title()), v] for g,v in brk("gender", "impressions", preset)],
                    "placement": [[PLAT.get(p,p.title()), v] for p,v in brk("publisher_platform", "spend", preset)],
                    "region":    [[regnm(r), v] for r, v in brk("region", "impressions", preset)]}
        d["aud_today"]     = audience("today")
        d["aud_yesterday"] = audience("yesterday")
        d["aud_30d"]       = audience("last_30d")

        def region_metrics(preset):
            try:
                rows = insights(level="account", date_preset=preset, breakdowns="region",
                                fields="spend,inline_link_clicks,actions")
            except Exception as e:
                print(f"  ⚠ lewati wilayah {preset} ({e})"); return []
            out = []
            for r in rows:
                sp = i(r, "spend")
                if sp <= 0:
                    continue
                out.append({"prov": regnm(str(r.get("region", "?"))), "spend": sp, "link": links(r)})
            out.sort(key=lambda x: -x["spend"])
            return out
        d["region_month"] = region_metrics("this_month")
        d["region_today"] = region_metrics("today")

        cache = {k: d.get(k) for k in HKEYS}
        cache["_ts"] = now_ts
        try:
            json.dump(cache, open(heavy_path(), "w", encoding="utf-8"), ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠ gagal simpan cache berat ({e})")
    else:
        print("• [hemat] pakai data berat dari cache (demografi/mingguan/wilayah update tiap jam) ...")
        for k in HKEYS:
            d[k] = heavy_cache.get(k, {} if k.startswith("aud_") else [])

    return d

def i2(row, key):
    """Ambil nilai numerik dari field array video_* (list of {action_type,value})."""
    lst = row.get(key) or []
    return int(round(float(lst[0]["value"]))) if lst else 0

# ---------- funnel dari Pixel (View LP / Klik WA / Contact) ----------
def pixel_stats(start, end):
    url = f"{BASE}/{PIXEL}/stats?" + urllib.parse.urlencode(
        {"aggregation": "event", "start_time": start, "end_time": end, "access_token": TOKEN})
    with urllib.request.urlopen(url, timeout=90) as r:
        res = json.load(r)
    tot = {}
    for b in res.get("data", []):
        for dd in b.get("data", []):
            tot[dd["value"]] = tot.get(dd["value"], 0) + int(dd["count"])
    return tot

def pixel_funnel():
    import time
    now = int(time.time()); start28 = now - 28 * 86400
    tmid = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    try:
        d28 = pixel_stats(start28, now); tod = pixel_stats(tmid, now)
    except Exception as e:
        print(f"  ⚠ Pixel belum bisa dibaca ({e}). Assign Pixel ke Pengguna Sistem dulu, lalu jalankan lagi.")
        return None
    m = lambda t: {"viewlp": t.get("PageView", 0), "viewcontent": t.get("ViewContent", 0),
                   "klikwa": t.get("AddToCart", 0), "contact": t.get("Contact", 0),
                   "purchase": t.get("Purchase", 0)}
    return {"d28": m(d28), "today": m(tod)}

# ---------- tulis hasil ----------
def write(data):
    with open(DATA_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    html = open(HTML_FILE, encoding="utf-8").read()
    block = "/* DATA-START */\nconst DATA = " + json.dumps(data, ensure_ascii=False) + ";\n/* DATA-END */"
    if "/* DATA-START */" not in html:
        sys.exit("❌ Penanda /* DATA-START */ tidak ada di novia-dashboard.html.")
    html = re.sub(r"/\* DATA-START \*/.*?/\* DATA-END \*/", lambda m: block, html, flags=re.S)
    open(HTML_FILE, "w", encoding="utf-8").write(html)

if __name__ == "__main__":
    print("Menarik data Meta Ads (multi-akun) ...")
    try:
        prev = json.load(open(DATA_JSON, encoding="utf-8"))
    except Exception:
        prev = {}
    prev_by_id = {a.get("id"): a for a in prev.get("accounts", [])}

    accounts_out = []
    for acc in ACCOUNTS:
        AD_ACCOUNT = acc["id"]                      # global dipakai build()
        print(f"\n=== Akun: {acc['name']} ({acc['id']}) ===")
        try:
            d = build()
            d["id"] = acc["id"]; d["name"] = acc["name"]
        except Exception as e:
            print(f"  ⚠ gagal tarik {acc['name']} ({e}) — pakai data sebelumnya bila ada")
            d = prev_by_id.get(acc["id"])
            if not d:
                continue
        accounts_out.append(d)

    if not accounts_out:
        print("\n❌ Tidak ada data akun yang berhasil ditarik.")
        sys.exit(1)

    out = {"generated_at": accounts_out[0].get("generated_at", ""), "accounts": accounts_out}
    write(out)
    print(f"\n✅ Selesai! {len(accounts_out)} akun · data per {out['generated_at']}.")
    print("   Buka (atau refresh) novia-dashboard.html.")
