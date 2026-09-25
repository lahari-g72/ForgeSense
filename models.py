from sqlalchemy import Column, Integer, String, Float
import database

class Telemetry(database.Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, index=True)
    temperature = Column(Float)
    status = Column(String)