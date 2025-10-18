from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/v1/report")
async def send_now(req: Request):
    data = await req.json()
    return {"ok": True}
