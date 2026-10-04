from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    project_name = Column(String)

    # latest user input
    latest_query = Column(String)

    # state of discovery
    question_mapping = Column(JSON)

    follow_up_questions = Column(JSON)

    # generated artifacts
    product_context = Column(JSON)

    market_search_query = Column(String)

    market_analysis = Column(JSON)

    customer_voice = Column(JSON)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

class Report(Base):
    """One generated investor memo for a project."""

    __tablename__ = "reports"

    id = Column(String(32), primary_key=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # pending -> running -> success | failed
    status = Column(String, nullable=False, default="pending")

    progress = Column(Integer, nullable=False, default=0)

    stage = Column(String)

    error = Column(String)

    product_name = Column(String)

    verdict = Column(String)

    readiness = Column(Integer)

    report_json = Column(JSON)

    pdf_filename = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
