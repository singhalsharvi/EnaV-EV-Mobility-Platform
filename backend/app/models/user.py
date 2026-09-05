from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    full_name = Column(String, nullable=True)
    account_category = Column(String, default="user", nullable=True)
    user_sub_type = Column(String, default="private", nullable=True)
    driver_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    total_distance_km = Column(Integer, default=142, nullable=True)
    co2_saved_kg = Column(Integer, default=28, nullable=True)

class UserProfile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    account_category = Column(String, default="user", nullable=True)
    user_sub_type = Column(String, default="private", nullable=True)
    driver_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)

class UserVehicle(Base):
    __tablename__ = "user_vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    vehicle_name = Column(String, default="Tata Nexon EV Max", nullable=False)
    vehicle_type = Column(String, default="SUV", nullable=False)
    battery_capacity_kwh = Column(Float, default=40.5, nullable=False)
    current_battery_percentage = Column(Float, default=78.0, nullable=False)
    range_km = Column(Float, default=320.0, nullable=False)

class UserJourney(Base):
    __tablename__ = "journeys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    distance_km = Column(Float, nullable=False)
    energy_used_kwh = Column(Float, nullable=False)
    co2_saved_kg = Column(Float, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)