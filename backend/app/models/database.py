"""
SQLAlchemy engine/session setup and ORM table definitions.

Schema mirrors the master plan's section 14, Database Design:
  USERS, FOODS, NUTRITION, MEALS, MEAL_ITEMS, FEEDBACK
"""
import os
import uuid

from sqlalchemy import (
    create_engine, Column, String, Float, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite:///./food_calorie.db"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=True)
    preferences = Column(String, nullable=True)  # JSON-encoded blob for v1

    meals = relationship("Meal", back_populates="user")


class Food(Base):
    __tablename__ = "foods"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=True)
    preparation = Column(String, nullable=True)

    nutrition = relationship("Nutrition", back_populates="food", uselist=False, cascade="all, delete-orphan")
    meal_items = relationship("MealItem", back_populates="food")


class Nutrition(Base):
    __tablename__ = "nutrition"
    food_id = Column(String, ForeignKey("foods.id"), primary_key=True)
    calories_100g = Column(Float, nullable=False)
    protein_100g = Column(Float, default=0)
    carbs_100g = Column(Float, default=0)
    fat_100g = Column(Float, default=0)
    fiber_100g = Column(Float, default=0)
    source = Column(String, default="usda_fdc")

    food = relationship("Food", back_populates="nutrition")


class Meal(Base):
    __tablename__ = "meals"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    image = Column(String, nullable=True)  # object storage key/URL
    total_calories = Column(Float, default=0)
    confidence = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")


class MealItem(Base):
    __tablename__ = "meal_items"
    id = Column(String, primary_key=True, default=_uuid)
    meal_id = Column(String, ForeignKey("meals.id"), nullable=False)
    food_id = Column(String, ForeignKey("foods.id"), nullable=False)
    estimated_weight = Column(Float, nullable=False)
    estimated_calories = Column(Float, nullable=False)
    confidence = Column(Float, default=0)

    meal = relationship("Meal", back_populates="items")
    food = relationship("Food", back_populates="meal_items")
    feedbacks = relationship("Feedback", back_populates="meal_item")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(String, primary_key=True, default=_uuid)
    meal_item_id = Column(String, ForeignKey("meal_items.id"), nullable=False)
    predicted_weight = Column(Float, nullable=False)
    corrected_weight = Column(Float, nullable=False)
    correction_type = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    meal_item = relationship("MealItem", back_populates="feedbacks")


def get_db():
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call once at startup, or use Alembic migrations
    in production instead of this."""
    Base.metadata.create_all(bind=engine)
