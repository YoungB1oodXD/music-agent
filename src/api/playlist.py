from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database import get_db
from src.manager.behavior_recorder import record_behavior
from src.models import Playlist, PlaylistSong, User

logger = logging.getLogger(__name__)
playlist_router = APIRouter(prefix="/api/playlists", tags=["playlists"])
like_router = APIRouter(prefix="/api/like", tags=["like"])


class CreatePlaylistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class PlaylistResponse(BaseModel):
    id: int
    user_id: int
    name: str
    is_system: bool
    created_at: datetime
    song_count: int = 0


class PlaylistDetailResponse(BaseModel):
    id: int
    user_id: int
    name: str
    is_system: bool
    created_at: datetime
    songs: list


class AddSongRequest(BaseModel):
    track_id: str = Field(..., min_length=1)
    title: str = ""
    artist: str = ""
    album: str = ""
    cover_url: str = ""
    duration: int = 0
    is_playable: bool = False
    audio_url: str = ""
    tags: list[str] = Field(default_factory=list)
    reason: str = ""


class SongResponse(BaseModel):
    id: int
    playlist_id: int
    track_id: str
    added_at: datetime
    title: str = ""
    artist: str = ""
    album: str = ""
    cover_url: str = ""
    duration: int = 0
    is_playable: bool = False
    audio_url: str = ""
    tags: list[str] = Field(default_factory=list)
    reason: str = ""


@playlist_router.get("", response_model=List[PlaylistResponse])
def get_playlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PlaylistResponse]:
    playlists = db.query(Playlist).filter(Playlist.user_id == current_user.id).all()
    result = []
    for p in playlists:
        result.append(
            PlaylistResponse(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                is_system=p.is_system,
                created_at=p.created_at,
                song_count=len(p.songs),
            )
        )
    return result


@playlist_router.post("", response_model=PlaylistResponse)
def create_playlist(
    req: CreatePlaylistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaylistResponse:
    playlist = Playlist(
        user_id=current_user.id,
        name=req.name,
        is_system=False,
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    logger.info(f"[PLAYLIST] Created: {playlist.name} by user {current_user.id}")
    return PlaylistResponse(
        id=playlist.id,
        user_id=playlist.user_id,
        name=playlist.name,
        is_system=playlist.is_system,
        created_at=playlist.created_at,
        song_count=0,
    )


@playlist_router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
def get_playlist(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaylistDetailResponse:
    playlist = (
        db.query(Playlist)
        .filter(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
        .first()
    )
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    songs = []
    for s in playlist.songs:
        songs.append(
            {
                "id": s.id,
                "track_id": s.track_id,
                "added_at": s.added_at,
                "title": s.title or "",
                "artist": s.artist or "",
                "album": s.album or "",
                "cover_url": s.cover_url or "",
                "duration": s.duration or 0,
                "is_playable": s.is_playable or False,
                "audio_url": s.audio_url or "",
                "tags": s.tags or [],
                "reason": s.reason or "",
            }
        )

    return PlaylistDetailResponse(
        id=playlist.id,
        user_id=playlist.user_id,
        name=playlist.name,
        is_system=playlist.is_system,
        created_at=playlist.created_at,
        songs=songs,
    )


@playlist_router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    playlist = (
        db.query(Playlist)
        .filter(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
        .first()
    )
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system playlist")

    db.delete(playlist)
    db.commit()
    logger.info(f"[PLAYLIST] Deleted: {playlist_id}")
    return {"ok": True}


@playlist_router.post("/{playlist_id}/songs", response_model=SongResponse)
def add_song_to_playlist(
    playlist_id: int,
    req: AddSongRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SongResponse:
    playlist = (
        db.query(Playlist)
        .filter(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
        .first()
    )
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    existing = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.track_id == req.track_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Song already in playlist")

    song = PlaylistSong(
        playlist_id=playlist_id,
        track_id=req.track_id,
        title=req.title,
        artist=req.artist,
        album=req.album,
        cover_url=req.cover_url,
        duration=req.duration,
        is_playable=req.is_playable,
        audio_url=req.audio_url,
        tags=req.tags,
        reason=req.reason,
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    song_name = f"{req.artist} - {req.title}" if req.artist else req.title
    record_behavior(
        user_id=str(current_user.id),
        song_id=req.track_id,
        behavior_type="add_to_playlist",
        song_name=song_name,
        session_id="",
        metadata={"playlist_id": playlist_id, "playlist_name": playlist.name},
        db=db,
    )
    logger.info(f"[PLAYLIST] Added song {req.track_id} to playlist {playlist_id}")
    return SongResponse(
        id=song.id,
        playlist_id=song.playlist_id,
        track_id=song.track_id,
        added_at=song.added_at,
        title=song.title or "",
        artist=song.artist or "",
        album=song.album or "",
        cover_url=song.cover_url or "",
        duration=song.duration or 0,
        is_playable=song.is_playable or False,
        audio_url=song.audio_url or "",
        tags=song.tags or [],
        reason=song.reason or "",
    )


@playlist_router.delete("/{playlist_id}/songs/{track_id}")
def remove_song_from_playlist(
    playlist_id: int,
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    playlist = (
        db.query(Playlist)
        .filter(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
        .first()
    )
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    song = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.track_id == track_id,
        )
        .first()
    )
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found in playlist")

    song_title = song.title or ""
    song_artist = song.artist or ""
    song_name = f"{song_artist} - {song_title}" if song_artist else song_title
    db.delete(song)
    db.commit()
    record_behavior(
        user_id=str(current_user.id),
        song_id=track_id,
        behavior_type="remove_from_playlist",
        song_name=song_name,
        session_id="",
        metadata={"playlist_id": playlist_id, "playlist_name": playlist.name},
        db=db,
    )
    logger.info(f"[PLAYLIST] Removed song {track_id} from playlist {playlist_id}")
    return {"ok": True}


def get_or_create_liked_playlist(user_id: int, db: Session) -> Playlist:
    playlist = (
        db.query(Playlist)
        .filter(
            Playlist.user_id == user_id,
            Playlist.is_system == True,
        )
        .first()
    )
    if playlist is None:
        playlist = Playlist(user_id=user_id, name="我的喜欢", is_system=True)
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
    return playlist


@like_router.post("/{track_id}", response_model=SongResponse)
def like_song(
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SongResponse:
    playlist = get_or_create_liked_playlist(current_user.id, db)

    existing = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist.id,
            PlaylistSong.track_id == track_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already liked")

    song = PlaylistSong(playlist_id=playlist.id, track_id=track_id)
    db.add(song)
    db.commit()
    db.refresh(song)
    record_behavior(
        user_id=str(current_user.id),
        song_id=track_id,
        behavior_type="like",
        song_name=track_id,
        session_id="",
        db=db,
    )
    logger.info(f"[LIKE] User {current_user.id} liked track {track_id}")
    return SongResponse(
        id=song.id,
        playlist_id=song.playlist_id,
        track_id=song.track_id,
        added_at=song.added_at,
    )


@like_router.delete("/{track_id}")
def unlike_song(
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    playlist = get_or_create_liked_playlist(current_user.id, db)

    song = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist.id,
            PlaylistSong.track_id == track_id,
        )
        .first()
    )
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")

    db.delete(song)
    db.commit()
    record_behavior(
        user_id=str(current_user.id),
        song_id=track_id,
        behavior_type="unlike",
        song_name=track_id,
        session_id="",
        db=db,
    )
    logger.info(f"[LIKE] User {current_user.id} unliked track {track_id}")
    return {"ok": True}


@like_router.get("", response_model=List[SongResponse])
def get_liked_songs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SongResponse]:
    playlist = get_or_create_liked_playlist(current_user.id, db)
    songs = db.query(PlaylistSong).filter(PlaylistSong.playlist_id == playlist.id).all()
    return [
        SongResponse(
            id=s.id, playlist_id=s.playlist_id, track_id=s.track_id, added_at=s.added_at
        )
        for s in songs
    ]
