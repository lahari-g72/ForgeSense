# ForgeSense

**Enterprise-Grade Industrial IoT Telemetry & Predictive Maintenance Platform**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)

ForgeSense is a high-throughput, full-stack data pipeline designed to ingest, analyze, and visualize real-time machine telemetry. Built to solve the core engineering challenges of IoT monitoring—network latency, database load, and state management—the platform processes live sensor data and detects mechanical anomalies instantly.

## Live Deployments
* **Frontend Application:** https://forge-sense.vercel.app
* **Backend API & Documentation:** https://forgesense-api.onrender.com/docs

---

## System Architecture

![ForgeSense System Architecture](architecture_diagram.png)

*(Note: For a deep-dive into the data pipeline, caching layers, and database schemas, please see `docs/architecture.md`)*

## Key Features
* **Real-Time Data Streaming:** Utilizes WebSockets to push live machine metrics to the dashboard with zero-latency.
* **Asynchronous Processing:** Offloads heavy database write operations to background threads to ensure the main API event loop remains unblocked during high-traffic spikes.
* **In-Memory Caching:** Integrates Redis to serve the latest machine state instantly, reducing relational database query loads.
* **Anomaly Detection:** Automatically flags critical thresholds (e.g., Temperature > 85.0C) and generates system alerts.
* **Secure Architecture:** Implements JWT-based authentication, strict CORS policies, and connection pooling for database resilience.

---

## Local Development Setup

### 1. Prerequisites
* Python 3.10+
* Node.js 18+
* PostgreSQL Database (or a cloud provider like Neon)
* Redis Instance (or a cloud provider like Upstash)

### 2. Environment Variables
Create a `.env` file in the root directory and add the following configuration:

```env
DATABASE_URL=postgresql://user:password@host/dbname
REDIS_URL=rediss://default:password@host:port 
```

3. Backend Setup
Open a terminal in the root directory and run:
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis passlib[bcrypt] python-jose python-dotenv

# Start the FastAPI server
uvicorn main:app --reload
The backend will be available at http://localhost:8000

4. Frontend Setup
Open a second terminal and navigate to the frontend directory:
cd forgesense-ui

# Install dependencies
npm install

# Start the Vite development server
npm run dev
The frontend will be available at http://localhost:5173

5. Running the Telemetry Simulator
To stream live data to the dashboard, open a third terminal in the root directory and run the IIoT device simulator:

python simulator.py

API Documentation
The backend provides automatic interactive API documentation via Swagger UI. Once the backend is running, navigate to /docs (e.g., http://localhost:8000/docs or https://forgesense-api.onrender.com/docs) to explore and test the available REST endpoints.

Core Endpoints
POST /register - Register a new user account.

POST /token - Authenticate and retrieve a JWT.

POST /setup - Seed the database with default Plant and Machine configurations.

POST /telemetry/ - Ingest new telemetry data (HTTP) and broadcast (WebSocket).

GET /telemetry/ - Retrieve paginated historical data.

GET /alerts/ - Fetch active system alerts.