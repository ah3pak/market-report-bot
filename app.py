from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"ok": True}

@app.post("/v1/report")
async def send_now(req: Request):
    # در برابر JSON خراب مقاوم:
    try:
        data = await req.json()
    except Exception:
        body = await req.body()
        data = {"raw": body.decode("utf-8", "ignore")}
    # اینجا فعلاً فقط برمی‌گردانیم تا مطمئن شویم 500 نمی‌گیریم
    return {"ok": True, "received": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
