import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Message, Track, SessionState, ChatSession } from '../types';
import api from '../services/api';
import { mapRecommendationsToTracks } from '../mappers/recommendations_to_tracks';
import { sendFeedback as sendFeedbackApi } from '../services/feedback';
import { refreshRecommendations } from '../services/chat';

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  messages: Message[];
  recommendations: Track[];
  sessionState: SessionState;
  isLoading: boolean;
  fetchSessions: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  sendFeedback: (songId: string, type: 'like' | 'dislike' | 'refresh') => Promise<void>;
  toggleLike: (songId: string) => Promise<void>;
  createNewSession: () => void;
}

const defaultSessionState: SessionState = {
  mood: '未知',
  scene: '未知',
  style: '未知',
  energy: '未知',
  vocal: '未知',
};

const initialMessage: Message = {
  id: '1',
  role: 'assistant',
  content: '你好！我是 Mustify，你的智能音乐助手。今天想听点什么样的音乐？',
  timestamp: Date.now(),
};

const _TOKEN_KEY = 'mustify_token';
const _CHAT_STORAGE_KEY = 'mustify-chat-v2';

let _prevToken: string | null = localStorage.getItem(_TOKEN_KEY);

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e: StorageEvent) => {
    if (e.key === _TOKEN_KEY) {
      const newToken = e.newValue;
      if (newToken !== _prevToken) {
        _prevToken = newToken;
        useChatStore.getState().createNewSession();
      }
    }
  });
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      messages: [initialMessage],
      recommendations: [],
      sessionState: defaultSessionState,
      isLoading: false,

      fetchSessions: async () => {
        try {
          const response = await api.get('/sessions');
          const raw = response.data.sessions || [];
          const sessions: ChatSession[] = raw.map((s: any) => ({
            id: s.session_id,
            title: s.first_message ? s.first_message.slice(0, 20) + (s.first_message.length > 20 ? '...' : '') : '新对话',
            createdAt: new Date(s.created_at).getTime(),
            messages: [],
            sessionState: { mood: '未知', scene: '未知', style: '未知', energy: '未知', vocal: '未知' },
          }));
          set({ sessions });
        } catch (err) {
          console.error('Failed to fetch sessions', err);
        }
      },

      loadSession: async (sessionId: string) => {
        try {
          const response = await api.get(`/sessions/${encodeURIComponent(sessionId)}`);
          const data = response.data;
          const messages: Message[] = (data.messages || []).map((m: any, i: number) => ({
            id: String(i),
            role: m.role,
            content: m.content,
            timestamp: m.timestamp || Date.now(),
            recommendations: m.recommendations || [],
          }));
          const sessionState: SessionState = {
            mood: data.session_state?.mood || '未知',
            scene: data.session_state?.scene || '未知',
            style: data.session_state?.style || '未知',
            energy: data.session_state?.energy || '未知',
            vocal: data.session_state?.vocal || '未知',
          };
          const recommendations = data.recommendations?.length > 0
            ? mapRecommendationsToTracks(data.recommendations)
            : [];
          set({
            currentSessionId: sessionId,
            messages,
            sessionState,
            recommendations,
          });
        } catch (err) {
          console.error('Failed to load session', err);
        }
      },

      deleteSession: async (sessionId: string) => {
        try {
          await api.delete(`/sessions/${encodeURIComponent(sessionId)}`);
          set({ sessions: get().sessions.filter(s => s.id !== sessionId) });
        } catch (err) {
          console.error('Failed to delete session', err);
        }
      },

      createNewSession: () => {
        set({
          currentSessionId: null,
          messages: [initialMessage],
          recommendations: [],
          sessionState: defaultSessionState,
        });
      },

      sendMessage: async (content) => {
        const userMessage: Message = {
          id: Date.now().toString(),
          role: 'user',
          content,
          timestamp: Date.now(),
        };

        const currentMessages = get().messages;
        set({
          messages: [...currentMessages, userMessage],
          isLoading: true,
        });

        try {
          const response = await api.post('/chat', {
            session_id: get().currentSessionId,
            message: content,
          });

          const { session_id, assistant_text, recommendations, state } = response.data;

          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: assistant_text,
            timestamp: Date.now(),
            recommendations: mapRecommendationsToTracks(recommendations),
          };

          const newMessages = [...get().messages, assistantMessage];
          const newSessionState: SessionState = {
            mood: state?.mood || '未知',
            scene: state?.scene || '未知',
            style: state?.genre || '未知',
            energy: state?.preferred_energy || '未知',
            vocal: state?.preferred_vocals || '未知',
          };

          set({
            messages: newMessages,
            recommendations: mapRecommendationsToTracks(recommendations) || [],
            sessionState: newSessionState,
            currentSessionId: session_id,
            isLoading: false,
          });

          get().fetchSessions();
        } catch (err) {
          set({ isLoading: false });
          console.error('Failed to send message', err);
        }
      },

      sendFeedback: async (songId, type) => {
        try {
          if (type === 'refresh') {
            const sessionId = get().currentSessionId;
            if (!sessionId) return;
            set({ isLoading: true });
            try {
              const result = await refreshRecommendations(sessionId);
              const tracks = mapRecommendationsToTracks(result.recommendations);
              set({ recommendations: tracks });
            } catch (err) {
              console.error('Failed to refresh recommendations', err);
            } finally {
              set({ isLoading: false });
            }
            return;
          }
          if (type === 'like' || type === 'dislike') {
            const track = get().recommendations.find(r => r.id === songId);
            const sessionId = get().currentSessionId || '';
            await sendFeedbackApi({
              session_id: sessionId,
              feedback_type: type,
              track_id: songId,
              track_metadata: track ? {
                title: track.title || track.name || '',
                artist: track.artist || '',
                genre: (track as Track).genre || '',
                tags: track.tags || [],
                duration: track.duration || 0,
              } : {},
            });
          }
        } catch (err) {
          console.error('Failed to send feedback', err);
        }
      },

      toggleLike: async (songId) => {
        try {
          await api.post(`/like/${songId}`);
        } catch (err) {
          console.error(err);
        }
      },
    }),
    {
      name: _CHAT_STORAGE_KEY,
      storage: {
        getItem: () => {
          const raw = localStorage.getItem(_CHAT_STORAGE_KEY);
          return raw ? JSON.parse(raw) : null;
        },
        setItem: (_, value) => {
          localStorage.setItem(_CHAT_STORAGE_KEY, JSON.stringify(value));
        },
        removeItem: () => {
          localStorage.removeItem(_CHAT_STORAGE_KEY);
        },
      },
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        messages: state.messages,
        recommendations: state.recommendations,
        sessionState: state.sessionState,
      } as ChatState),
    }
  )
);
