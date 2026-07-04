import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class PriceType(str, enum.Enum):
    RENT = "rent"
    SALE = "sale"
    BOTH = "both"


class PropertyType(str, enum.Enum):
    CONDO = "condo"
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    APARTMENT = "apartment"
    OTHER = "other"


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Price
    price_rent = Column(Float, nullable=True)  # Monthly rent in THB
    price_sale = Column(Float, nullable=True)  # Sale price in THB
    currency = Column(String(3), default="THB")
    price_type = Column(SAEnum(PriceType), nullable=False)

    # Property details
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    area_sqm = Column(Float, nullable=True)
    floor = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    furnished = Column(Boolean, nullable=True)
    property_type = Column(SAEnum(PropertyType), nullable=False)

    # Location
    address = Column(String(500), nullable=True)
    district = Column(String(100), nullable=True, index=True)
    sub_district = Column(String(100), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # Source
    source = Column(String(50), nullable=False, index=True)
    source_url = Column(String(1000), nullable=True)
    source_id = Column(String(200), nullable=True)
    images = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    posted_date = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Relationships
    price_history = relationship("PriceHistory", back_populates="property", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    price_rent = Column(Float, nullable=True)
    price_sale = Column(Float, nullable=True)
    price_type = Column(SAEnum(PriceType), nullable=False)
    source = Column(String(50), nullable=True)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    property = relationship("Property", back_populates="price_history")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(100), nullable=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    wechat_openid = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(200), nullable=True)
    preferred_language = Column(String(5), default="zh")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    comparisons = relationship("Comparison", back_populates="user", cascade="all, delete-orphan")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    property = relationship("Property", foreign_keys=[property_id])


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    property_ids = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    user = relationship("User", back_populates="comparisons")
