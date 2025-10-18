from fastapi import FastAPI, Request, HTTPException
import os, json, httpx
import uvicorn

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"ok": True}

async def send_telegram(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        raise HTTPException(status_code=500, detail="Bot token or chat id missing")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()

def build_text_from_payload(data: dict) -> str:
    """
    اگر data['text'] باشد مستقیماً همان را می‌فرستد.
    وگرنه تلاش می‌کند از بخش‌های gold/fx/crypto متن را بسازد.
    """
    if isinstance(data, dict) and "text" in data:
        return data["text"]

    # ساخت متن ساده از فیلدهای اختیاری
    lines = []
    lines.append("📊 گزارش روز بازار طلا، ارز و رمزارزها")
    if "date_line" in data:
        lines.append(data["date_line"])
    if "gold" in data:
        lines.append("\n🟡 بازار طلا")
        lines.append(data["gold"])
    if "fx" in data:
        lines.append("\n💵 بازار ارز")
        lines.append(data["fx"])
    if "crypto" in data:
        lines.append("\n🪙 بازار رمزارزها")
        lines.append(data["crypto"])
    return "\n".join(lines).strip()

@app.post("/v1/report")
async def send_now(req: Request):
    # JSON خراب هم هندل می‌شود
    try:
        data = await req.json()
        if not isinstance(data, dict):
            data = {"raw": data}
    except Exception:
        body = await req.body()
        data = {"text": body.decode("utf-8","ignore")}

    text = build_text_from_payload(data)
    res = await send_telegram(text)
    return {"ok": True, "telegram": res}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
