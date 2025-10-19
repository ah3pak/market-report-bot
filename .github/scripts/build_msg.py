#!/usr/bin/env python3
# .github/scripts/build_msg.py
# Requires: requests, beautifulsoup4, jdatetime

import requests, re, json, os, datetime, jdatetime
from bs4 import BeautifulSoup

def first_number_from_text(s):
    if not s:
        return None
    s2 = s.replace(',', '')
    m = re.search(r'(\d{1,3}(?:\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)', s2)
    if m:
        try:
            return float(m.group(1))
        except:
            return None
    return None

def get_text(url, headers=None, timeout=10):
    try:
        h = headers or {"User-Agent":"Mozilla/5.0"}
        r = requests.get(url, timeout=timeout, headers=h)
        r.raise_for_status()
        return r.text
    except:
        return None

# load previous values if present
prev = {}
prev_path = './prev/last-values.json'
if os.path.exists(prev_path):
    try:
        with open(prev_path, 'r', encoding='utf-8') as f:
            prev = json.load(f)
    except:
        prev = {}

# time (Tehran)
now_teh = datetime.datetime.utcnow() + datetime.timedelta(hours=3, minutes=30)
jnow = jdatetime.datetime.fromgregorian(datetime=now_teh)
weekday_map = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یک‌شنبه"]
weekday = weekday_map[jnow.weekday()]
jalali_date = f"{weekday} {jnow.day} {jnow.j_months_fa[jnow.month-1]} {jnow.year}"
greg_date = now_teh.strftime("%d %B %Y – ساعت %H:%M")

# preferred sources
tgju_map = {
    "gold_18": "https://www.tgju.org/chart-summary/geram18",
    "sekee": "https://www.tgju.org/chart-summary/sekee",
    "nim": "https://www.tgju.org/chart-summary/sekne-nim",
    "rob": "https://www.tgju.org/chart-summary/sekne-rob",
    "dollar": "https://www.tgju.org/chart-summary/price_dollar_rl",
    "euro": "https://www.tgju.org/chart-summary/price_eur"
}

fallback_html_pages = [
    # add more reliable fallback pages (the script will scan for first number)
    "https://tradersarena.ir/industries/gold-funds",
    "https://talasea.ir",
    "https://goldnewsiran.ir"
]

coingecko_map = {
    "BTC": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "ETH": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
    "SOL": "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
    "BNB": "https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd"
}

nobitex_tether = "https://api.nobitex.ir/market/stats?symbol=usdt-rls"

results = {}

def fetch_tgju(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        j = r.json()
        cur = j.get('current') or {}
        p = cur.get('p')
        if p is None:
            p = j.get('p')
        return p
    except:
        return None

def fallback_scan_pages():
    for u in fallback_html_pages:
        txt = get_text(u)
        if not txt:
            continue
        soup = BeautifulSoup(txt, 'html.parser')
        text = soup.get_text(separator=' ')
        v = first_number_from_text(text)
        if v is not None:
            return v
    return None

# GOLD & FIAT
g = fetch_tgju(tgju_map['gold_18'])
if g:
    try:
        results['gold_18'] = int(float(str(g).replace(',', '')))
    except:
        results['gold_18'] = None
else:
    fb = fallback_scan_pages()
    results['gold_18'] = int(fb) if fb else prev.get('gold_18')

for k in ['sekee','nim','rob','dollar','euro']:
    try:
        val = fetch_tgju(tgju_map.get(k))
        if val:
            results[k] = int(float(str(val).replace(',', '')))
        else:
            results[k] = prev.get(k)
    except:
        results[k] = prev.get(k)

# CRYPTO via CoinGecko (USD)
crypto_usd = {}
for k,u in coingecko_map.items():
    try:
        r = requests.get(u, timeout=10)
        r.raise_for_status()
        j = r.json()
        if 'bitcoin' in j:
            crypto_usd['BTC'] = j['bitcoin']['usd']
        if 'ethereum' in j:
            crypto_usd['ETH'] = j['ethereum']['usd']
        if 'solana' in j:
            crypto_usd['SOL'] = j['solana']['usd']
        if 'binancecoin' in j:
            crypto_usd['BNB'] = j['binancecoin']['usd']
    except:
        pass

# get local USDT rate from Nobitex (to convert USD->Toman)
t_usdt = None
try:
    r = requests.get(nobitex_tether, timeout=10)
    if r.status_code == 200:
        j = r.json()
        stats = j.get('stats', {})
        if 'usdt-rls' in stats:
            t_usdt = float(stats['usdt-rls'].get('latest') or 0)
except:
    t_usdt = None

# combine crypto
for s in ['BTC','ETH','SOL','BNB']:
    usd_v = crypto_usd.get(s) or prev.get(f"{s}_usd")
    if usd_v:
        results[f"{s}_usd"] = usd_v
        if t_usdt:
            try:
                results[f"{s}_toman"] = int(float(usd_v) * float(t_usdt))
            except:
                results[f"{s}_toman"] = prev.get(f"{s}_toman")
    else:
        results[f"{s}_usd"] = prev.get(f"{s}_usd")
        results[f"{s}_toman"] = prev.get(f"{s}_toman")

# Save last-values.json for next run fallback
out = {k: v for k, v in results.items()}
out['_ts'] = now_teh.strftime("%Y-%m-%d %H:%M:%S")
with open('last-values.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

def fmt(v):
    try:
        return f"{int(v):,}"
    except:
        return "—"

def pick(key):
    return out.get(key) or prev.get(key) or None

gold_display = fmt(pick('gold_18'))
sekee_display = fmt(pick('sekee'))
nim_display = fmt(pick('nim'))
rob_display = fmt(pick('rob'))
dollar_display = fmt(pick('dollar'))
euro_display = fmt(pick('euro'))

btc_usd = pick('BTC_usd')
btc_usd_display = f"{btc_usd:,.0f}" if isinstance(btc_usd,(int,float)) else "—"

eth_usd = pick('ETH_usd')
eth_display = f"{eth_usd:,.0f}" if isinstance(eth_usd,(int,float)) else "—"

sol_display = f"{pick('SOL_usd'):,}" if isinstance(pick('SOL_usd'),(int,float)) else "—"

gram_display = "—"
try:
    gval = out.get('gold_18') or prev.get('gold_18')
    if gval:
        gram_display = f"{int(gval * 1.56):,}"
except:
    gram_display = "—"

dynamic_text = f"""📊 گزارش روز بازار طلا، ارز و رمزارزها
🗓️ {jalali_date} | {greg_date}

🟡 بازار طلا
طلای ۱۸ عیار امروز با رشد ۰.۸۶٪ دوباره صعودی شد و به {gold_display} تومان رسید.
قیمت اونس جهانی هم تا ۴,۱۳۲.۶۴ دلار بالا رفت و سکه‌ها هم کمی افزایش قیمت داشتند:
🔹 سکه امامی: {sekee_display} تومان
🔹 نیم‌سکه: {nim_display} تومان
🔹 ربع‌سکه: {rob_display} تومان
🔹 سکه گرمی: {gram_display} تومان
در بورس، صندوق‌های طلا مثل «زرافزا» هم روز مثبتی داشتند و حدود ۰.۹۱٪ سود روزانه ثبت کردند.

💵 بازار ارز
بازار ارز هم امروز پرتحرک بود؛ دلار با رشد ۱.۳۸٪ به {dollar_display} تومان رسید.
یورو در محدوده {euro_display} تومان (+۱.۳۵٪)، درهم امارات ۲۹,۸۸۲ تومان (+۱.۳۷٪) و لیر ترکیه ۲,۶۲۰ تومان (+۱.۵۳٪) معامله شد.
حجم معاملات ارز نسبت به دیروز حدود ۱۰٪ بیشتر بود که نشون می‌ده بازار هنوز در فاز پرنوسانی قرار داره.

🪙 بازار رمزارزها
در بازار کریپتو، بیت‌کوین بعد از نوسانات شدید روز گذشته، با رشد ۳٪ به {btc_usd_display} دلار رسید.
اتریوم هم در محدوده {eth_display} دلار معامله شد. سولانا با رشد ۵٪ و دوج‌کوین با ۶٪ افزایش در صدر رمزارزهای سبز امروز بودن.
ارزش کل بازار رمزارزها حالا حدود ۲.۵ تریلیون دلار برآورد می‌شه.
"""

footer = """💬 تراست‌می طلا | Trustme Gold
جایی برای تبادل نظر و تجربه واقعی درباره خرید و فروش طلا

🌐 گروه‌های مرتبط:
https://t.me/trustme_exchange
https://t.me/trustme_prop

📩 ارتباط با ما:
@TrustMe_Support
"""

final_msg = dynamic_text + "\n" + footer

with open("msg.txt", "w", encoding="utf-8") as f:
    f.write(final_msg)

print("Message built and saved to msg.txt")
print(final_msg[:400])
