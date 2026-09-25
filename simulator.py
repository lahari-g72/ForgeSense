import os
import time
import random
import requests
import json
from datetime import datetime
import redis
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Securely connect to Upstash Redis, bypassing strict SSL checks for local dev
redis_url = os.getenv("REDIS_URL")
if redis_url:
    r = redis.from_url(
        redis_url, 
        decode_responses=True,
        ssl_cert_reqs="none"
    )
else:
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        password=os.getenv("REDIS_PASSWORD"),
        ssl=True,
        ssl_cert_reqs="none",
        decode_responses=True
    )

API_URL = "http://127.0.0.1:8000/telemetry/"
MACHINES = ["CNC-001", "CNC-002", "MILL-001"]

def generate_telemetry(machine_id: str):
    base_temp = 75.0 if "CNC" in machine_id else 65.0
    base_vib = 5.0 if "CNC" in machine_id else 3.5
    
    temperature = base_temp + random.uniform(-5.0, 15.0)
    vibration = base_vib + random.uniform(-2.0, 5.0)
    
    return {
        "machine_id": machine_id,
        "temperature": round(temperature, 2),
        "vibration": round(vibration, 2),
        "pressure": round(120.0 + random.uniform(-10.0, 10.0), 2),
        "rpm": round(2500 + random.uniform(-200, 200), 2),
        "power_consumption": round(15.0 + random.uniform(-2.0, 2.0), 2)
    }

print("Starting multi-machine ForgeSense Simulator...")
print("Press CTRL+C to stop.")

try:
    while True:
        for machine_id in MACHINES:
            data = generate_telemetry(machine_id)
            
            try:
                requests.post(API_URL, json=data)
            except Exception as e:
                print(f"API Error for {machine_id}: {e}")
                
            r.set(f"telemetry:{machine_id}", json.dumps(data), ex=60)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Broadcasted telemetry for {len(MACHINES)} machines")
        time.sleep(2)
except KeyboardInterrupt:
    print("\nSimulator stopped.")