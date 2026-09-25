from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import database
import models
import schemas

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# NEW: THE WEBSOCKET CONNECTION MANAGER
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# ==========================================
# NEW: WEBSOCKET ENDPOINT
# ==========================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open and listening
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==========================================
# UPDATED: REST API ROUTES
# ==========================================
# NEW: In-memory cache to track the previous temperature of each machine
last_known_temps = {}

@app.post("/telemetry/", response_model=schemas.TelemetryResponse)
async def create_telemetry(telemetry: schemas.TelemetryCreate, db: Session = Depends(get_db)):
    # 1. Save to Database
    db_telemetry = models.Telemetry(
        machine_id=telemetry.machine_id, 
        temperature=telemetry.temperature,
        status=telemetry.status
    )
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    
    # 2. Algorithmic Anomaly Detection
    anomaly_alert = None
    previous_temp = last_known_temps.get(telemetry.machine_id)
    
    if previous_temp is not None:
        temp_spike = telemetry.temperature - previous_temp
        # If temperature jumps more than 10 degrees instantly, trigger an anomaly
        if temp_spike > 10.0:
            anomaly_alert = f"ANOMALY: {telemetry.machine_id} spiked by {temp_spike:.1f}°C!"
            
    # Update the in-memory state for the next reading
    last_known_temps[telemetry.machine_id] = telemetry.temperature
    
    # 3. Broadcast standard telemetry
    await manager.broadcast({
        "type": "telemetry",
        "data": {
            "id": db_telemetry.id,
            "machine_id": db_telemetry.machine_id,
            "temperature": db_telemetry.temperature,
            "status": db_telemetry.status
        }
    })
    
    # 4. Broadcast high-priority alert if anomaly detected
    if anomaly_alert:
        await manager.broadcast({
            "type": "alert",
            "message": anomaly_alert
        })
        
    return db_telemetry

@app.get("/telemetry/", response_model=list[schemas.TelemetryResponse])
def read_telemetry(db: Session = Depends(get_db)):
    return db.query(models.Telemetry).order_by(models.Telemetry.id.desc()).limit(50).all()

# NEW: Endpoint to acknowledge and clear alerts
@app.post("/acknowledge/{machine_id}")
async def acknowledge_alert(machine_id: str):
    # This broadcasts a message to all connected React dashboards to clear the alert
    await manager.broadcast({
        "type": "clear_alert",
        "machine_id": machine_id
    })
    return {"message": f"Alert cleared for {machine_id}"}