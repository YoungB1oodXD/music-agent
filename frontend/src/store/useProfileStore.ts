import { create } from 'zustand';
import { UserPreference, UserBehaviorStats } from '../types';
import { profileApi } from '../services/api';
import { useChatStore } from './useChatStore';

interface ProfileState {
  preferences: UserPreference | null;
  stats: UserBehaviorStats | null;
  isLoading: boolean;
  fetchProfile: (userId: number) => Promise<void>;
  clearPreferences: (userId: number) => Promise<void>;
}

export const useProfileStore = create<ProfileState>((set) => ({
  preferences: null,
  stats: null,
  isLoading: false,

  fetchProfile: async (userId: number) => {
    set({ isLoading: true });
    const sessionId = useChatStore.getState().currentSessionId;
    const params = sessionId ? { session_id: sessionId } : {};
    try {
      // Try GET /ai/portrait first (with session_id for deep analysis)
      const response = await profileApi.get<UserPreference>('/ai/portrait', { params });
      set({ preferences: response.data, isLoading: false });
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } };
      if (error.response?.status === 404) {
        // No portrait yet — trigger generation
        try {
          const genRes = await profileApi.post<UserPreference>('/ai/generate-portrait', undefined, { params });
          set({ preferences: genRes.data, isLoading: false });
        } catch (genErr) {
          console.error('Failed to generate portrait', genErr);
          set({ isLoading: false });
        }
      } else {
        console.error('Failed to fetch portrait', err);
        set({ isLoading: false });
      }
    }
  },

  clearPreferences: async (userId: number) => {
    set({ isLoading: true });
    try {
      await profileApi.delete('/ai/portrait');
    } catch (e) {
      console.error('Failed to clear portrait', e);
    }
    // After clearing, fetchProfile will 404 and trigger regeneration
    const sessionId = useChatStore.getState().currentSessionId;
    const params = sessionId ? { session_id: sessionId } : {};
    try {
      const genRes = await profileApi.post<UserPreference>('/ai/generate-portrait', undefined, { params });
      set({ preferences: genRes.data, isLoading: false });
    } catch (genErr) {
      console.error('Failed to regenerate portrait', genErr);
      set({ isLoading: false, preferences: null });
    }
  },
}));
