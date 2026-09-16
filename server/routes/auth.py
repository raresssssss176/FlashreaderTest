"""
server/routes/auth.py
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.models import Device
from server.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


class PairDeviceRequest(BaseModel):
    device_code: str
    owner_name: str


@router.post("/pair")
def pair_device(req: PairDeviceRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_code == req.device_code).first()
    if not device:
        device = Device(device_code=req.device_code, owner_name=req.owner_name)
        db.add(device)
    else:
        device.owner_name = req.owner_name
    db.commit()
    return {"status": "success", "message": f"Device {req.device_code} paired."}