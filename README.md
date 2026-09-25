#  ForgeSense

**Enterprise-Grade Industrial IoT Telemetry & Predictive Maintenance Platform**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)

ForgeSense is a high-throughput, full-stack data pipeline designed to ingest, analyze, and visualize real-time machine telemetry. Built to solve the core engineering challenges of IoT monitoring—network latency, database load, and state management—the platform processes live sensor data and detects mechanical anomalies instantly.

##  System Architecture

```mermaid
graph TD
    A[IoT Simulator (Python)] -->|REST POST /telemetry| B(FastAPI Backend)
    B -->|Persist History| C[(Cloud PostgreSQL)]
    B -->|In-Memory Analytics| D{Anomaly Engine}
    D -->|Push Telemetry Stream| E[WebSockets]
    D -->|Push Priority Alerts| E
    E -->|Bi-Directional Async| F[React + TS Dashboard]
    F -->|REST POST /acknowledge| B