import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

import logging
from app.database import engine, Base, get_db, SessionLocal
from app.models import user, vehicle, ev_station
from app.services import db_models
from app.routers import telemetry, auth, ev_stations, routes, command_center, emergency_report, infra_planner
from app.schemas.dashboard import DashboardSummaryResponse

logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as db_err:
    logger.warning(f"Database table initialization skipped: {db_err}")

app = FastAPI(title="EnaV Backend", version="1.0.0")

@app.on_event("startup")
def on_startup():
    """
    On service boot, guarantee that all database tables are present
    and seed baseline emergency vehicles & demo accounts if missing.
    """
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            # 1. Seed baseline emergency vehicles into SQL registry if table is empty
            from app.services.vehicle_repository import SQLEmergencyVehicleRepository
            repo = SQLEmergencyVehicleRepository(db)
            vehicles = repo.get_all_vehicles()
            logger.info(f"Verified {len(vehicles)} emergency vehicles in database registry.")

            # 2. Seed demo user accounts if not present
            # 2. Seed demo user accounts and profiles if not present
            import uuid
            from app.models.user import User, UserProfile
            from app.routers.auth import pwd_context
            demo_accounts = [
                ("admin@gov.in", "EnaV@Admin2026", "government", "Rajesh Sharma", "Delhi Transport Department", "MUNICIPAL-ADMIN-01"),
                ("driver@gov.in", "EnaV@Driver2026", "gov_driver", "Vikram Singh", "Municipal Transport Fleet", "GOV-DRV-102"),
                ("user@example.com", "EnaV@User2026", "user", "Ananya Verma", None, None),
            ]
            for demo_email, demo_pwd, demo_role, demo_name, demo_dept, demo_badge in demo_accounts:
                existing = db.query(User).filter(User.email == demo_email).first()
                hashed = pwd_context.hash(demo_pwd)
                if not existing:
                    db.add(User(
                        email=demo_email,
                        hashed_password=hashed,
                        role=demo_role,
                        full_name=demo_name,
                        account_category="government" if demo_role == "government" else "user",
                        user_sub_type="government_admin" if demo_role == "government" else ("gov_driver" if demo_role == "gov_driver" else "private"),
                        driver_id=demo_badge,
                        department=demo_dept,
                        total_distance_km=142,
                        co2_saved_kg=28
                    ))
                else:
                    existing.hashed_password = hashed
                    existing.full_name = demo_name
                    existing.role = demo_role
                    existing.account_category = "government" if demo_role == "government" else "user"
                    existing.user_sub_type = "government_admin" if demo_role == "government" else ("gov_driver" if demo_role == "gov_driver" else "private")
                    existing.driver_id = demo_badge
                    existing.department = demo_dept

                # Also ensure UserProfile exists
                prof = db.query(UserProfile).filter(UserProfile.email == demo_email).first()
                if not prof:
                    db.add(UserProfile(
                        id=str(uuid.uuid4()),
                        email=demo_email,
                        full_name=demo_name,
                        account_category="government" if demo_role == "government" else "user",
                        user_sub_type="gov_driver" if demo_role == "gov_driver" else "private",
                        driver_id=demo_badge,
                        department=demo_dept
                    ))
                else:
                    prof.full_name = demo_name
                    prof.department = demo_dept
                    prof.driver_id = demo_badge
            db.commit()
            logger.info("Verified baseline demo user accounts and profiles.")
        finally:
            db.close()
    except Exception as err:
        logger.warning(f"Startup database seeding skipped: {err}")


cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [
    origin.strip()
    for origin in cors_origins_env.split(",")
    if origin.strip()
]
if "http://localhost:3000" not in allowed_origins:
    allowed_origins.append("http://localhost:3000")
if "http://127.0.0.1:3000" not in allowed_origins:
    allowed_origins.append("http://127.0.0.1:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.render\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(telemetry.router)
app.include_router(auth.router)
app.include_router(ev_stations.router)
app.include_router(routes.router)
app.include_router(command_center.router)
app.include_router(emergency_report.router)
app.include_router(infra_planner.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to EnaV EV Mobility API"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EnaV Backend", "timestamp": datetime.utcnow().isoformat()}