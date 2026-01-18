# This work is licensed under the terms of the MIT license
import datetime
from enum import Enum as EnumType

import cuid2
from db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum

cuid = cuid2.Cuid()


class MemberRole(EnumType):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    BANNED = "banned"


class User(Base):
    __tablename__ = "users"
    user_id = Column(
        String(24), primary_key=True, nullable=False, unique=True, default=cuid.generate
    )
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    date_created = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    date_updated = Column(
        DateTime,
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )
    rooms = relationship(
        "Room_members", back_populates="user", cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )


class Room(Base):
    __tablename__ = "rooms"
    room_id = Column(
        String(24), primary_key=True, nullable=False, unique=True, default=cuid.generate
    )
    room_name = Column(String(255), nullable=False, unique=False)
    date_created = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    date_updated = Column(
        DateTime,
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )
    members = relationship(
        "Room_members", back_populates="room", cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message", back_populates="room", cascade="all, delete-orphan"
    )


class Room_members(Base):
    __tablename__ = "room_members"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(24), ForeignKey("users.user_id"), nullable=False)
    room_id = Column(String(24), ForeignKey("rooms.room_id"), nullable=False)
    member_role = Column(
        Enum(MemberRole, name="member_role"), nullable=False, default=MemberRole.MEMBER
    )
    join_date = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    user = relationship("User", back_populates="rooms")
    room = relationship("Room", back_populates="members")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender = Column(String(24), ForeignKey("users.user_id"), nullable=False)
    room_id = Column(String(24), ForeignKey("rooms.room_id"), nullable=False)
    message = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    date_updated = Column(
        DateTime,
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")
