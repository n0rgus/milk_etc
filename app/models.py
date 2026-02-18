from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from .db import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    buy_freq = Column(String, nullable=True)
    buy_qty = Column(Float, nullable=True)
    preferred_store = Column(String, nullable=True)

    links = relationship("StoreLink", back_populates="item", cascade="all, delete-orphan")
    prices = relationship("PriceHistory", back_populates="item", cascade="all, delete-orphan")


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    links = relationship("StoreLink", back_populates="store", cascade="all, delete-orphan")
    prices = relationship("PriceHistory", back_populates="store", cascade="all, delete-orphan")


class StoreLink(Base):
    __tablename__ = "store_links"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    store_label = Column(String, nullable=True)   # product name as known in that store
    url = Column(Text, nullable=True)

    item = relationship("Item", back_populates="links")
    store = relationship("Store", back_populates="links")

    __table_args__ = (
        UniqueConstraint("item_id", "store_id", name="uq_item_store"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    price = Column(Float, nullable=True)
    was_price = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    promo_text = Column(String, nullable=True)
    discount_percent = Column(Float, nullable=True)

    item = relationship("Item", back_populates="prices")
    store = relationship("Store", back_populates="prices")


class CaptureRun(Base):
    __tablename__ = "capture_runs"
    id = Column(Integer, primary_key=True)
    store = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CaptureRunItem(Base):
    __tablename__ = "capture_run_items"
    id = Column(Integer, primary_key=True)
    capture_run_id = Column(Integer, ForeignKey("capture_runs.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("capture_run_id", "item_id", "store_id", name="uq_capture_run_item_store"),
    )


class ShopSession(Base):
    __tablename__ = "shop_sessions"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ShopPurchase(Base):
    __tablename__ = "shop_purchases"
    id = Column(Integer, primary_key=True)
    shop_session_id = Column(Integer, ForeignKey("shop_sessions.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    purchased_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("shop_session_id", "item_id", name="uq_shop_item"),
    )
