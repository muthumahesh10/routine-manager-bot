from sqlalchemy import Column, Integer, String, Time, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from database import Base

class RoleEnum(enum.Enum):
    admin = "admin"
    user = "user"

class FrequencyEnum(enum.Enum):
    daily = "daily"
    weekday = "weekday"
    weekend = "weekend"
    monthly_1st = "monthly_1st"
    monthly_6th = "monthly_6th"

class StatusEnum(enum.Enum):
    pending = "pending"
    completed = "completed"
    missed = "missed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.user)

    templates = relationship("TaskTemplate", back_populates="user")
    logs = relationship("DailyLog", back_populates="user")

class TaskTemplate(Base):
    __tablename__ = "task_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_name = Column(String, nullable=False)
    start_time = Column(Time, nullable=True) # e.g., 04:00:00
    end_time = Column(Time, nullable=True)   # e.g., 06:00:00
    frequency = Column(Enum(FrequencyEnum), nullable=False)

    user = relationship("User", back_populates="templates")
    logs = relationship("DailyLog", back_populates="task")

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("task_templates.id"))
    date = Column(Date, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)

    user = relationship("User", back_populates="logs")
    task = relationship("TaskTemplate", back_populates="logs")

class DailyJournal(Base):
    __tablename__ = "daily_journals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    entry = Column(String, nullable=False)

    user = relationship("User")