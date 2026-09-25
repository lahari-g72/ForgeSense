from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

# --- TELEMETRY ---
class TelemetryBase(BaseModel):
    machine_id: str
    temperature: float
    vibration: float
    pressure: float
    rpm: float
    power_consumption: float

class TelemetryCreate(TelemetryBase):
    pass

class TelemetryResponse(TelemetryBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- ALERTS ---
class AlertBase(BaseModel):
    machine_id: str
    message: str
    is_acknowledged: bool = False

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- MACHINES ---
class MachineBase(BaseModel):
    id: str
    plant_id: int
    status: str = "Healthy"

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    telemetry: List[TelemetryResponse] = []
    alerts: List[AlertResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- PLANTS ---
class PlantBase(BaseModel):
    name: str
    location: str

class PlantCreate(PlantBase):
    pass

class PlantResponse(PlantBase):
    id: int
    machines: List[MachineResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- AUTHENTICATION ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

class Token(BaseModel):
    access_token: str
    token_type: str