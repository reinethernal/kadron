from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    anonymous = Column(Boolean, default=False)
    time_limit = Column(DateTime)
    scheduled_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"))
    text = Column(Text)
    type = Column(String)
    options = Column(Text)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    category = Column(String, default="Новичок")
    last_activity = Column(DateTime, default=datetime.utcnow)
    warnings = Column(Integer, default=0)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer)
    user_id = Column(Integer)
    timestamp = Column(DateTime)


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"))
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    user_id = Column(Integer)
    answer = Column(Text)
    timestamp = Column(DateTime)
