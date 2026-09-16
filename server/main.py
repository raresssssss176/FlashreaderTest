"""
server/main.py
"""

from fastapi import FastAPI
import uvicorn
from server.database import engine
from server.models import Base
from server.routes import auth, store

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FlashReader Server API")

# Register route modules
app.include_router(auth.router)
app.include_router(store.router)


@app.get("/")
def root():
    return {"status": "online", "system": "FlashReader Cloud Backend"}


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)