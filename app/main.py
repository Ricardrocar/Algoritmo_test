from fastapi import FastAPI
from app.routes import email_routes

app = FastAPI(title="Gmail Analyzer API", version="0.1.0")
app.include_router(email_routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}


