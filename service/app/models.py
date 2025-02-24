import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(String, unique=True, index=True, nullable=False)

    wallets = relationship("Wallet", back_populates="owner")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, nullable=False)
    private_key = Column(String, nullable=False)
    mnemonic = Column(String, nullable=False)
    balance = Column(String, default="0")
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="wallets")
    orders = relationship("Order", back_populates="wallet")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        String, unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    order_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(
        String, default="pending"
    )  #TODO Добавить enum pending, executed, cancelled, error и т.п.
    tx_hash = Column(String, nullable=True)
    jetton_address = Column(String, nullable=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)

    wallet = relationship("Wallet", back_populates="orders")
