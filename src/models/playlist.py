from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from src.database.db import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    songs = relationship(
        "PlaylistSong", back_populates="playlist", cascade="all, delete-orphan"
    )


class PlaylistSong(Base):
    __tablename__ = "playlist_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(
        Integer, ForeignKey("playlists.id"), nullable=False, index=True
    )
    track_id = Column(String(50), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Full song metadata for persistence
    title = Column(String(200), default="")
    artist = Column(String(200), default="")
    album = Column(String(200), default="")
    cover_url = Column(String(500), default="")
    duration = Column(Integer, default=0)
    is_playable = Column(Boolean, default=False)
    audio_url = Column(String(500), default="")
    tags = Column(JSON, default=list)
    reason = Column(String(500), default="")

    playlist = relationship("Playlist", back_populates="songs")
