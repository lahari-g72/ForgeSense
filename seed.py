from database import SessionLocal
import models

db = SessionLocal()

# We assume Plant 1 exists from your earlier setup
new_machines = ["CNC-002", "MILL-001"]

for m_id in new_machines:
    existing = db.query(models.Machine).filter(models.Machine.id == m_id).first()
    if not existing:
        new_machine = models.Machine(id=m_id, plant_id=1, status="Healthy")
        db.add(new_machine)
        print(f"Added {m_id} to database.")

db.commit()
db.close()
print("Database seeding complete!")