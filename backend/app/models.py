# This work is licensed under the terms of the MIT license
import datetime

import cuid2
from db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

cuid = cuid2.Cuid()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(24), nullable=False, unique=True, default=cuid.generate)
    password_hash = Column(String(255), nullable=False)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender = Column(String(24), ForeignKey("users.user_id"), nullable=False)
    message = Column(String(255), nullable=False)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
