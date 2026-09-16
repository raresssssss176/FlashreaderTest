"""
server/main.py

Run with:  python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
Then open http://127.0.0.1:8000/admin to upload books.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.database import engine, ensure_schema
from server.models import Base
from server.pipeline.analyzer import nlp_status
from server.routes import admin, auth, store

Base.metadata.create_all(bind=engine)
ensure_schema()

app = FastAPI(title="FlashReader Server API", version="0.2.0")

# The device is on the same LAN, not the same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(store.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "system": "FlashReader Cloud Backend",
        "nlp": nlp_status(),
        "admin_ui": "/admin",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
