import os
import json
import redis
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
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

# --- CORS SECURITY CONFIGURATION ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://forge-sense.vercel.app",
    "https://forge-sense-git-main-lll-53f0.vercel.app",
    "https://forge-sense-niong74ss-lll-53f0.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# --- THREAD POOL FOR BACKGROUND TASKS ---
executor = ThreadPoolExecutor(max_workers=10)

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
            try:
                await connection.send_json(message)
            except Exception:
                pass

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

def process_telemetry_background(telemetry_data: dict):
    """Executes in a separate worker thread — completely independent of FastAPI's event loop."""
    db = SessionLocal()
    try:
        # 1. Validate machine
        machine = db.query(models.Machine).filter(models.Machine.id == telemetry_data["machine_id"]).first()
        if not machine:
            print(f"Ignored payload: Machine {telemetry_data['machine_id']} not found.")
            return

        # 2. Update Redis Cache
        redis_client.setex(
            f"telemetry_cache:{telemetry_data['machine_id']}", 
            60, 
            json.dumps(telemetry_data)
        )

        # 3. Save standard telemetry
        db_telemetry = models.Telemetry(**telemetry_data)
        db.add(db_telemetry)

        # 4. Check for anomalies
        is_anomalous = False
        alert_msg = ""
        if telemetry_data["temperature"] > 85.0:
            is_anomalous = True
            alert_msg = f"Critical Temperature: {telemetry_data['temperature']}°C"
        elif telemetry_data["vibration"] > 8.0:
            is_anomalous = True
            alert_msg = f"Critical Vibration: {telemetry_data['vibration']} mm/s"

        # 5. Create alert
        if is_anomalous:
            db_alert = models.Alert(machine_id=telemetry_data["machine_id"], message=alert_msg)
            db.add(db_alert)
            machine.status = "Critical"

        db.commit()
    except Exception as e:
        print(f"Background worker error: {e}")
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
    
    if machine_id:
        query = query.filter(models.Telemetry.machine_id == machine_id)
        
    if sort_by == "desc":
        query = query.order_by(models.Telemetry.timestamp.desc())
    else:
        query = query.order_by(models.Telemetry.timestamp.asc())
        
    return query.offset(skip).limit(limit).all()

@app.post("/telemetry/", status_code=status.HTTP_202_ACCEPTED)
async def create_telemetry(telemetry: schemas.TelemetryCreate):
    """Instantly accepts telemetry, emits WebSockets, and offloads DB I/O to a dedicated thread."""
    payload = telemetry.model_dump()

    # 1. Fast WebSocket broadcast (Local memory, 0ms network latency)
    await manager.broadcast({
        "type": "TELEMETRY", 
        "data": payload
    })

    # 2. Fire-and-forget to separate thread (Never blocks event loop or response)
    executor.submit(process_telemetry_background, payload)

    return {"message": "Telemetry received and queued"}

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