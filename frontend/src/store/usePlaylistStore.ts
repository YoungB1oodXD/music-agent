import { create } from 'zustand';
import { Playlist, Song } from '../types';
import api from '../services/api';

interface PlaylistState {
  playlists: Playlist[];
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  fetchPlaylists: () => Promise<void>;
  fetchPlaylistSongs: (playlistId: string) => Promise<Song[]>;
  createPlaylist: (name: string) => Promise<boolean>;
  addSongToPlaylist: (playlistId: string, song: Song) => Promise<void>;
  removeSongFromPlaylist: (playlistId: string, trackId: string) => Promise<void>;
  deletePlaylist: (playlistId: string) => Promise<void>;
  toggleLike: (trackId: string, isLiked: boolean) => Promise<void>;
}

export const usePlaylistStore = create<PlaylistState>((set, get) => ({
  playlists: [],
  isLoading: false,
  isCreating: false,
  error: null,

  fetchPlaylists: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/playlists');
      set({ playlists: response.data, isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: 'Failed to load playlists' });
    }
  },

  fetchPlaylistSongs: async (playlistId) => {
    try {
      const response = await api.get(`/playlists/${playlistId}`);
      const playlist = response.data;
      
      set((state) => ({
        playlists: state.playlists.map((p) => 
          p.id === playlistId ? { ...p, songs: playlist.songs } : p
        )
      }));
      
      return playlist.songs || [];
    } catch (err) {
      console.error('Failed to fetch playlist songs', err);
      return [];
    }
  },

  createPlaylist: async (name) => {
    set({ isCreating: true, error: null });
    try {
      const response = await api.post('/playlists', { name });
      set((state) => ({ 
        playlists: [...state.playlists, response.data],
        isCreating: false 
      }));
      return true;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create playlist';
      set({ isCreating: false, error: errorMsg });
      return false;
    }
  },

  addSongToPlaylist: async (playlistId, song) => {
    try {
      await api.post(`/playlists/${playlistId}/songs`, { 
        track_id: song.id,
        title: song.title || "",
        artist: song.artist || "",
        album: song.album || "",
        cover_url: song.coverUrl || "",
        duration: song.duration || 0,
        is_playable: song.isPlayable || false,
        audio_url: song.audioUrl || "",
        tags: song.tags || [],
        reason: song.reason || song.recommendationReason || "",
      });
      const response = await api.get('/playlists');
      set({ playlists: response.data });
    } catch (err) {
      console.error('Failed to add song to playlist', err);
    }
  },

  removeSongFromPlaylist: async (playlistId, trackId) => {
    try {
      await api.delete(`/playlists/${playlistId}/songs/${trackId}`);
      const response = await api.get('/playlists');
      set({ playlists: response.data });
      const detailRes = await api.get(`/playlists/${playlistId}`);
      return detailRes.data.songs || [];
    } catch (err) {
      console.error('Failed to remove song from playlist', err);
      return [];
    }
  },

  deletePlaylist: async (playlistId) => {
    try {
      await api.delete(`/playlists/${playlistId}`);
      await get().fetchPlaylists();
    } catch (err) {
      console.error('Failed to delete playlist', err);
    }
  },

  toggleLike: async (trackId, isLiked) => {
    try {
      if (isLiked) {
        await api.delete(`/like/${trackId}`);
      } else {
        await api.post(`/like/${trackId}`);
      }
      // Refresh playlists as "My Likes" might be a system playlist
      const response = await api.get('/playlists');
      set({ playlists: response.data });
    } catch (err) {
      console.error('Failed to toggle like', err);
    }
  },
}));
