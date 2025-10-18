from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"ok": True}

@app.post("/v1/report")
async def send_now(req: Request):
    data = await req.json()
    print("Received data:", data)
    return {"ok": True, "message": "Report received successfully."}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
