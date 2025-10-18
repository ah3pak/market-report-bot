from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def health():
    return {"ok": True}
