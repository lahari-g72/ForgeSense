from locust import HttpUser, task, between
import random
class ForgeSenseMachine(HttpUser):
    # Simulate realistic machine intervals (1 to 2 seconds)
    wait_time = between(1.0, 2.0)

    @task
    def send_telemetry(self):
        payload = {
            "machine_id": "CNC-001",
            "temperature": round(random.uniform(60.0, 80.0), 2),
            "vibration": round(random.uniform(1.0, 5.0), 2),
            "pressure": round(random.uniform(30.0, 45.0), 2),
            "rpm": round(random.uniform(2900.0, 3100.0), 2),
            "power_consumption": round(random.uniform(10.0, 15.0), 2)
        }
        # Post the data to our API
        self.client.post("/telemetry/", json=payload)