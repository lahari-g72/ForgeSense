from pydantic import BaseModel

class TelemetryCreate(BaseModel):
    machine_id: str
    temperature: float
    status: str

class TelemetryResponse(TelemetryCreate):
    id: int

    class Config:
        from_attributes = True