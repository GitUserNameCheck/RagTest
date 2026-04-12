from typing import Annotated
from fastapi import Depends
from sqlalchemy import ForeignKey, String, create_engine 
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session, relationship

from app.core.config import config

engine = create_engine(config.db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    s3_filename: Mapped[str] = mapped_column(unique=True)
    s3_mime_type: Mapped[str]
    reports: Mapped[list["Report"]] = relationship(
        cascade="all, delete-orphan"
    )

class Report(Base):
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"))
    s3_filename: Mapped[str] = mapped_column(unique=True)
    tag: Mapped[str]
    