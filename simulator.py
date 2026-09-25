import time
import random
import requests

API_URL = "http://127.0.0.1:8000/telemetry/"
MACHINES = ["Machine-A (Lathe)", "Machine-B (CNC)", "Machine-C (Welder)"]

print("Starting ForgeSense Simulator (with Anomaly Injection)...")

while True:
    for machine in MACHINES:
        # Normal operating temperature
        temp = round(random.uniform(60.0, 80.0), 1)
        
        # 10% chance to simulate a massive mechanical failure (temperature spike!)
        if random.random() < 0.10:
            temp += random.uniform(15.0, 25.0)
            
        status = "Critical" if temp > 90.0 else "Warning" if temp > 80.0 else "Healthy"
            
        try:
            requests.post(API_URL, json={"machine_id": machine, "temperature": temp, "status": status})
            print(f"Sent {machine}: {temp}°C")
        except:
            pass
            
    time.sleep(3)