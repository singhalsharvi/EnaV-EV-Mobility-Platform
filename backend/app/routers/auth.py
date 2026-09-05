import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User, UserProfile, UserVehicle, UserJourney

router = APIRouter(tags=["Authentication & Profiles"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "sha256_crypt", "argon2", "bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str
    password: str
    role: Optional[str] = "user"
    full_name: Optional[str] = None
    account_category: Optional[str] = None
    user_sub_type: Optional[str] = None
    driver_id: Optional[str] = None
    department: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str

class VehicleSaveRequest(BaseModel):
    user_id: int
    vehicle_name: str
    vehicle_type: str
    battery_capacity_kwh: Optional[float] = 40.5
    current_battery_percentage: Optional[float] = 78.0
    range_km: Optional[float] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if pwd_context.verify(plain_password, hashed_password):
            return True
    except Exception:
        pass
    # Allow seamless fallback for demo passwords
    demo_passwords = {
        "admin123": "EnaV@Admin2026",
        "driver123": "EnaV@Driver2026",
        "user123": "EnaV@User2026",
    }
    if plain_password in demo_passwords:
        try:
            return pwd_context.verify(demo_passwords[plain_password], hashed_password)
        except Exception:
            pass
    return False

# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Resolve target role from frontend account_category & user_sub_type
    target_role = "user"
    if user.account_category == "government" or user.role == "government":
        target_role = "government"
    elif user.user_sub_type == "gov_driver" or user.role == "gov_driver":
        target_role = "gov_driver"
    elif user.role:
        target_role = user.role

    name = user.full_name or user.email.split("@")[0]
    hashed_password = pwd_context.hash(str(user.password)[:72])

    account_cat = user.account_category or ("government" if target_role == "government" else "user")
    user_sub = user.user_sub_type or ("government_admin" if target_role == "government" else ("gov_driver" if target_role == "gov_driver" else "private"))

    default_driver_id = user.driver_id
    if not default_driver_id:
        if target_role == "gov_driver":
            default_driver_id = f"GOV-DRV-102"
        elif target_role == "government":
            default_driver_id = f"MUNICIPAL-ADMIN-01"

    default_dept = user.department
    if not default_dept:
        if target_role == "government":
            default_dept = "City Mobility Operations"
        elif target_role == "gov_driver":
            default_dept = "Municipal Transport Agency"

    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        role=target_role,
        full_name=name,
        account_category=account_cat,
        user_sub_type=user_sub,
        driver_id=default_driver_id,
        department=default_dept,
        total_distance_km=142,
        co2_saved_kg=28
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Upsert into profiles table safely
    try:
        existing_prof = db.query(UserProfile).filter(UserProfile.email == user.email).first()
        if not existing_prof:
            new_prof = UserProfile(
                id=str(uuid.uuid4()),
                full_name=name,
                email=user.email,
                account_category=account_cat,
                user_sub_type=user_sub,
                driver_id=default_driver_id,
                department=default_dept
            )
            db.add(new_prof)
            db.commit()
    except Exception:
        db.rollback()

    # Create baseline vehicle for driver/user
    existing_veh = db.query(UserVehicle).filter(UserVehicle.user_id == new_user.id).first()
    if not existing_veh and target_role != "government":
        db.add(UserVehicle(
            user_id=new_user.id,
            vehicle_name="Tata Nexon EV Max",
            vehicle_type="SUV",
            battery_capacity_kwh=40.5,
            current_battery_percentage=78.0,
            range_km=320.0
        ))
        db.commit()

    token = f"mock-jwt-token-{new_user.email}"
    return {
        "message": "User registered successfully",
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = f"mock-jwt-token-{db_user.email}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": db_user.id,
        "email": db_user.email,
        "role": db_user.role,
        "full_name": db_user.full_name or db_user.email.split("@")[0]
    }

@router.get("/auth/users/me")
def get_current_user_profile(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    prof = None
    try:
        prof = db.query(UserProfile).filter(UserProfile.email == email).first()
    except Exception:
        pass

    name = user.full_name or (prof.full_name if prof else None) or user.email.split("@")[0]
    category = user.account_category or (prof.account_category if prof else None) or ("government" if user.role == "government" else "user")
    sub_type = user.user_sub_type or (prof.user_sub_type if prof else None) or ("government_admin" if user.role == "government" else ("gov_driver" if user.role == "gov_driver" else "private"))
    driver_id = user.driver_id or (prof.driver_id if prof else None) or ("MUNICIPAL-ADMIN-01" if user.role == "government" else "DRV-102")
    department = user.department or (prof.department if prof else None) or ("City Mobility Operations" if user.role == "government" else "Transport Operations")

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": name,
        "account_category": category,
        "user_sub_type": sub_type,
        "driver_id": driver_id,
        "department": department,
        "total_distance_km": user.total_distance_km or 142,
        "co2_saved_kg": user.co2_saved_kg or 28
    }

@router.post("/auth/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = pwd_context.hash(request.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

# ---------------------------------------------------------------------------
# User Vehicle & Journey Endpoints for Profiles
# ---------------------------------------------------------------------------

@router.get("/vehicle/user/{user_id}")
def get_user_vehicle(user_id: int, db: Session = Depends(get_db)):
    veh = db.query(UserVehicle).filter(UserVehicle.user_id == user_id).first()
    if not veh:
        # Provide default registered vehicle for driver profile
        veh = UserVehicle(
            user_id=user_id,
            vehicle_name="Tata Nexon EV Max",
            vehicle_type="SUV",
            battery_capacity_kwh=40.5,
            current_battery_percentage=78.0,
            range_km=320.0
        )
        try:
            db.add(veh)
            db.commit()
            db.refresh(veh)
        except Exception:
            pass

    return {
        "id": veh.id if veh else 1,
        "user_id": user_id,
        "vehicle_name": veh.vehicle_name if veh else "Tata Nexon EV Max",
        "vehicle_type": veh.vehicle_type if veh else "SUV",
        "battery_capacity_kwh": veh.battery_capacity_kwh if veh else 40.5,
        "current_battery_percentage": veh.current_battery_percentage if veh else 78.0,
        "range_km": veh.range_km if veh else 320.0
    }

@router.post("/vehicle/save")
def save_user_vehicle(data: VehicleSaveRequest, db: Session = Depends(get_db)):
    veh = db.query(UserVehicle).filter(UserVehicle.user_id == data.user_id).first()
    if veh:
        veh.vehicle_name = data.vehicle_name
        veh.vehicle_type = data.vehicle_type
        if data.battery_capacity_kwh is not None:
            veh.battery_capacity_kwh = data.battery_capacity_kwh
        if data.current_battery_percentage is not None:
            veh.current_battery_percentage = data.current_battery_percentage
        if data.range_km is not None:
            veh.range_km = data.range_km
    else:
        veh = UserVehicle(
            user_id=data.user_id,
            vehicle_name=data.vehicle_name,
            vehicle_type=data.vehicle_type,
            battery_capacity_kwh=data.battery_capacity_kwh or 40.5,
            current_battery_percentage=data.current_battery_percentage or 78.0,
            range_km=data.range_km or 320.0
        )
        db.add(veh)
    db.commit()
    return {"message": "Vehicle profile saved successfully"}

@router.get("/journey/user/{user_id}")
def get_user_journeys(user_id: int, db: Session = Depends(get_db)):
    journeys = db.query(UserJourney).filter(UserJourney.user_id == user_id).order_by(UserJourney.id.desc()).all()
    if not journeys:
        # Provide representative initial journeys for active dashboard visualization
        return [
            {
                "id": 101,
                "source": "Janakpuri West",
                "destination": "Connaught Place, Central Delhi",
                "distance_km": 18.5,
                "energy_used_kwh": 2.6,
                "co2_saved_kg": 3.4,
                "completed_at": datetime.utcnow().isoformat()
            },
            {
                "id": 102,
                "source": "Indira Gandhi Airport (Terminal 3)",
                "destination": "Aerocity Smart Hub",
                "distance_km": 6.2,
                "energy_used_kwh": 0.9,
                "co2_saved_kg": 1.2,
                "completed_at": datetime.utcnow().isoformat()
            }
        ]
    return journeys