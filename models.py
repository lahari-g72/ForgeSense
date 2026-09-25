from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Plant(Base):
    __tablename__ = "plants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    
    # Relationship to machines
    machines = relationship("Machine", back_populates="plant")

class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(String, primary_key=True, index=True) # e.g., "CNC-001"
    plant_id = Column(Integer, ForeignKey("plants.id"))
    status = Column(String, default="Healthy")
    
    # Relationships
    plant = relationship("Plant", back_populates="machines")
    telemetry = relationship("Telemetry", back_populates="machine")
    alerts = relationship("Alert", back_populates="machine")

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Expanded Enterprise Metrics
    temperature = Column(Float)
    vibration = Column(Float)
    pressure = Column(Float)
    rpm = Column(Float)
    power_consumption = Column(Float)
    
    # Relationship
    machine = relationship("Machine", back_populates="telemetry")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, ForeignKey("machines.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(String)
    is_acknowledged = Column(Boolean, default=False)
    
    # Relationship
    machine = relationship("Machine", back_populates="alerts")

class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="viewer") # Roles: admin, engineer, viewer