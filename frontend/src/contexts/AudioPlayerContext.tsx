import React, { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react';

interface AudioPlayerContextType {
  playingTrackId: string | null;
  playTrack: (trackId: string, audioUrl: string) => Promise<{ success: boolean; error?: string }>;
  pauseTrack: () => void;
  isPlaying: (trackId: string) => boolean;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | null>(null);

export function AudioPlayerProvider({ children }: { children: React.ReactNode }) {
  const [playingTrackId, setPlayingTrackId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const pendingTrackIdRef = useRef<string | null>(null);

  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'none';
    
    const handlePlay = () => {
      const pendingId = pendingTrackIdRef.current;
      if (pendingId) {
        setPlayingTrackId(pendingId);
        pendingTrackIdRef.current = null;
      }
    };
    
    const handlePause = () => {
      setPlayingTrackId(null);
    };
    
    const handleEnded = () => {
      setPlayingTrackId(null);
      pendingTrackIdRef.current = null;
    };
    
    const handleError = () => {
      const errorCode = audio.error?.code;
      const errorMessage = audio.error?.message || 'Unknown error';
      console.error(`Audio playback error (code ${errorCode}):`, errorMessage);
      setPlayingTrackId(null);
      pendingTrackIdRef.current = null;
    };
    
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audioRef.current = audio;
    
    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.pause();
      audio.src = '';
    };
  }, []);

  const playTrack = useCallback(async (trackId: string, audioUrl: string): Promise<{ success: boolean; error?: string }> => {
    const audio = audioRef.current;
    if (!audio) {
      return { success: false, error: 'Audio player not initialized' };
    }

    if (playingTrackId === trackId) {
      audio.pause();
      return { success: true };
    }

    audio.pause();
    audio.src = audioUrl;
    pendingTrackIdRef.current = trackId;
    
    try {
      await audio.play();
      return { success: true };
    } catch (error) {
      pendingTrackIdRef.current = null;
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Failed to play audio:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [playingTrackId]);

  const pauseTrack = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
    }
    setPlayingTrackId(null);
    pendingTrackIdRef.current = null;
  }, []);

  const isPlaying = useCallback((trackId: string) => {
    return playingTrackId === trackId;
  }, [playingTrackId]);

  return (
    <AudioPlayerContext.Provider value={{ playingTrackId, playTrack, pauseTrack, isPlaying }}>
      {children}
    </AudioPlayerContext.Provider>
  );
}

export function useAudioPlayer() {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useAudioPlayer must be used within AudioPlayerProvider');
  }
  return context;
}