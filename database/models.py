from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import declarative_base

from datetime import datetime

Base = declarative_base()


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    telegram_id = Column(
        BigInteger,
        unique=True,
        nullable=False
    )

    username = Column(
        String(255)
    )

    first_seen = Column(
        DateTime,
        default=datetime.utcnow
    )

    last_seen = Column(
        DateTime,
        default=datetime.utcnow
    )


class Song(Base):

    __tablename__ = "songs"

    id = Column(
        Integer,
        primary_key=True
    )

    title = Column(
        String(500),
        nullable=False
    )

    youtube_url = Column(
        String,
        nullable=False
    )

    download_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Download(Base):

    __tablename__ = "downloads"

    id = Column(
        Integer,
        primary_key=True
    )

    telegram_id = Column(
        BigInteger,
        nullable=False
    )

    song_id = Column(
        Integer,
        ForeignKey("songs.id"),
        nullable=False
    )

    file_type = Column(
        String(20)
    )

    status = Column(
        String(20)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )