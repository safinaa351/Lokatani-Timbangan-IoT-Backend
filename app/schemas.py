from pydantic import BaseModel

class IoTWeightUpdate(BaseModel):
    weight: float
    device_id: str

class BatchCreate(BaseModel):
    weights: list[float]
    photo_url: str