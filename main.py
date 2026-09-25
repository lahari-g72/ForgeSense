import os
import json
import redis
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from typing import Optional
import models
import schemas
from database import engine, get_db, SessionLocal
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import status
import auth


# Auto-generate database tables based on models.py
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ForgeSense Enterprise API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REDIS CACHE SETUP ---
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL not found in environment variables.")

# decode_responses=True ensures we get clean strings back instead of raw bytes
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, ssl_cert_reqs="none")

# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- AUTHENTICATION & SECURITY ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT to see who is making the request
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except auth.jwt.JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register", response_model=schemas.Token)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pw, role=user.role)
    db.add(new_user)
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- API ENDPOINTS ---
@app.post("/setup", status_code=201)
def setup_initial_data(db: Session = Depends(get_db)):
    """Creates a default plant and machine so we have foreign keys to attach telemetry to."""
    plant = db.query(models.Plant).first()
    if not plant:
        plant = models.Plant(name="Alpha Manufacturing", location="Sector 7")
        db.add(plant)
        db.commit()
        db.refresh(plant)
        
        machine = models.Machine(id="CNC-001", plant_id=plant.id)
        db.add(machine)
        db.commit()
        return {"message": "Database seeded with default Plant and Machine (CNC-001)"}
    return {"message": "Database already seeded"}

async def process_anomalies(telemetry: schemas.TelemetryCreate):
    db = SessionLocal()
    try:
        is_anomalous = False
        alert_msg = ""

        if telemetry.temperature > 85.0:
            is_anomalous = True
            alert_msg = f"Critical Temperature: {telemetry.temperature}°C"
        elif telemetry.vibration > 8.0:
            is_anomalous = True
            alert_msg = f"Critical Vibration: {telemetry.vibration} mm/s"

        if is_anomalous:
            db_alert = models.Alert(machine_id=telemetry.machine_id, message=alert_msg)
            db.add(db_alert)

            machine = db.query(models.Machine).filter(models.Machine.id == telemetry.machine_id).first()
            if machine:
                machine.status = "Critical"

            db.commit()

            # Simulated external notification (e.g., triggering a Slack webhook)
            await manager.broadcast({
                "type": "ALERT", 
                "data": {"machine_id": telemetry.machine_id, "message": alert_msg}
            })
    finally:
        db.close()


@app.get("/telemetry/", response_model=List[schemas.TelemetryResponse])
def get_telemetry_history(
    machine_id: Optional[str] = None,
    sort_by: str = "desc",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieve historical telemetry with pagination, filtering, and sorting."""
    query = db.query(models.Telemetry)
    
    # 1. Filtering
    if machine_id:
        query = query.filter(models.Telemetry.machine_id == machine_id)
        
    # 2. Sorting
    if sort_by == "desc":
        query = query.order_by(models.Telemetry.timestamp.desc())
    else:
        query = query.order_by(models.Telemetry.timestamp.asc())
        
    # 3. Pagination
    return query.offset(skip).limit(limit).all()

@app.post("/telemetry/", response_model=schemas.TelemetryResponse)
async def create_telemetry(
    telemetry: schemas.TelemetryCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    machine = db.query(models.Machine).filter(models.Machine.id == telemetry.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # 1. Save standard telemetry instantly
    db_telemetry = models.Telemetry(**telemetry.model_dump())
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)

    # 2. Update Redis RAM cache
    redis_client.setex(
        f"telemetry_cache:{telemetry.machine_id}", 
        60, 
        json.dumps(telemetry.model_dump())
    )

    # 3. Broadcast standard metrics to UI
    await manager.broadcast({
        "type": "TELEMETRY", 
        "data": telemetry.model_dump()
    })

    # 4. Offload heavy anomaly evaluation to the background worker
    background_tasks.add_task(process_anomalies, telemetry)

    return db_telemetry

@app.get("/telemetry/{machine_id}/latest")
def get_cached_telemetry(machine_id: str):
    """Fetches the latest telemetry directly from Redis RAM cache."""
    cached_data = redis_client.get(f"telemetry_cache:{machine_id}")
    if cached_data:
        return {"source": "redis_cache", "data": json.loads(cached_data)}
    raise HTTPException(status_code=404, detail="No cached data available")

@app.get("/alerts/", response_model=List[schemas.AlertResponse])
def get_active_alerts(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # This route is now protected! Only users with a valid token can see this.
    return db.query(models.Alert).filter(models.Alert.is_acknowledged == False).all()
@app.patch("/alerts/{alert_id}/acknowledge", response_model=schemas.AlertResponse)
def acknowledge_alert(
    alert_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Marks a specific alert as acknowledged so it clears from the active dashboard."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.is_acknowledged:
        raise HTTPException(status_code=400, detail="Alert is already acknowledged")

    alert.is_acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)