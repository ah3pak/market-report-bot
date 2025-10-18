import os, textwrap, jdatetime, datetime, pytz, json
from fastapi import FastAPI, Request, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

TZ = pytz.timezone("Europe/Istanbul")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # مثلا: -1001234567890
if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

bot = Bot(BOT_TOKEN)
app = FastAPI(title="MarketReportAPI")
LATEST_DATA = {}

def fmt_num(n):
    if n is None: return "-"
    try: return f"{int(n):,}".replace(",", "٬")
    except: return str(n)

def build_message(d):
    # تاریخ‌ها
    if not d.get("date_shamsi"):
        today = jdatetime.datetime.fromgregorian(datetime=datetime.datetime.now(TZ))
        d["date_shamsi"] = today.strftime("%Y/%m/%d")
    if not d.get("date_greg"):
        d["date_greg"] = datetime.datetime.now(TZ).strftime("%Y-%m-%d")

    g = d.get("gold", {})
    fx = d.get("fx", {})
    c = d.get("crypto", {})
    coins = g.get("coins", {})
    funds_summary = g.get("funds_summary", "")

    ch = g.get("g18_change_pct", 0)
    trend = "افزایش" if ch > 0 else ("افت" if ch < 0 else "بدون تغییر")
    gold_line = f"طلای ۱۸ عیار امروز {trend} {abs(ch):.2f}٪ داشت و به {fmt_num(g.get('g18_price'))} تومان رسید."
    oz = g.get('ounce_usd')
    ounce_line = f"قیمت اونس جهانی هم در محدوده {oz} دلار بود." if oz else ""

    msg = textwrap.dedent(f"""
    📊 گزارش روز بازار طلا، ارز و رمزارزها
    🗓️ {d['date_shamsi']} | {d['date_greg']} – ساعت ۲۱:۰۰

    🟡 بازار طلا
    {gold_line}
    {ounce_line}
    🔹 سکه امامی: {fmt_num(coins.get('emami'))} تومان
    🔹 نیم‌سکه: {fmt_num(coins.get('nim'))} تومان
    🔹 ربع‌سکه: {fmt_num(coins.get('rob'))} تومان
    🔹 سکه گرمی: {fmt_num(coins.get('grami'))} تومان
    {('در بورس، ' + funds_summary) if funds_summary else ''}

    💵 بازار ارز
    دلار: {fmt_num(fx.get('usd', {}).get('price'))} ({fx.get('usd', {}).get('change_pct','-')}٪) | یورو: {fmt_num(fx.get('eur', {}).get('price'))} ({fx.get('eur', {}).get('change_pct','-')}٪)
    درهم: {fmt_num(fx.get('aed', {}).get('price'))} ({fx.get('aed', {}).get('change_pct','-')}٪) | لیر: {fmt_num(fx.get('try', {}).get('price'))} ({fx.get('try', {}).get('change_pct','-')}٪)

    🪙 بازار رمزارزها
    BTC: ${c.get('btc_usd','-')} | ETH: ${c.get('eth_usd','-')} | SOL: ${c.get('sol_usd','-')} | DOGE: ${c.get('doge_usd','-')}
    ارزش کل بازار رمزارزها حدود {c.get('total_mcap_usd_trillion','-')} تریلیون دلار برآورد می‌شود.
    """).strip()
    return msg

def send_saved_report():
    if not LATEST_DATA:  # اگر چیزی ذخیره نشده، ارسال نکن
        return
    payload = json.loads(json.dumps(LATEST_DATA))
    msg = build_message(payload)
    bot.send_message(chat_id=CHAT_ID, text=msg)

# زمان‌بندی روزانه ساعت ۲۱:۰۰
scheduler = BackgroundScheduler(timezone=TZ)
scheduler.add_job(send_saved_report, "cron", hour=21, minute=0)
scheduler.start()

app = app

@app.post("/v1/report")
async def send_now(req: Request):
    data = await req.json()
    try:
        msg = build_message(data)
        bot.send_message(chat_id=CHAT_ID, text=msg)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/v1/report/schedule")
async def save_and_schedule(req: Request):
    data = await req.json()
    global LATEST_DATA
    LATEST_DATA = data
    return {"ok": True, "scheduled": "daily 21:00 Europe/Istanbul"}

@app.get("/healthz")
def health():
    return {"ok": True}