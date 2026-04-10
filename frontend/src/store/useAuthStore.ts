import { create } from 'zustand';
import { User } from '../types';
import api from '../services/api';
import { useChatStore } from './useChatStore';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: any) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const TOKEN_KEY = 'mustify_token';

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem(TOKEN_KEY),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/auth/login', credentials);
      const { access_token, user } = response.data;
      localStorage.setItem(TOKEN_KEY, access_token);
      set({ token: access_token, user, isAuthenticated: true, isLoading: false });
      useChatStore.getState().createNewSession();
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message, isLoading: false });
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/auth/register', data);
      const { access_token, user } = response.data;
      localStorage.setItem(TOKEN_KEY, access_token);
      set({ token: access_token, user, isAuthenticated: true, isLoading: false });
      useChatStore.getState().createNewSession();
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('mustify-chat');
    localStorage.removeItem('mustify-playlists');
    set({ user: null, token: null, isAuthenticated: false });
    useChatStore.getState().createNewSession();
  },

  checkAuth: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    set({ isLoading: true });
    try {
      const response = await api.get('/auth/me');
      set({ user: response.data, isAuthenticated: true, isLoading: false });
    } catch (err) {
      localStorage.removeItem(TOKEN_KEY);
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
