import api from '../services/api';
import { RefreshResponse } from '../types';

export interface ChatState {
  mood?: string | null;
  scene?: string | null;
  genre?: string | null;
  preferred_energy?: string | null;
  preferred_vocals?: string | null;
}

export interface RecommendationObject {
  id: string;
  name: string;
  reason?: string | null;
  citations: string[];
  genre?: string;
  genre_description?: string;
  tags?: string[];
  is_playable?: boolean;
  audio_url?: string;
}

export interface ChatResponse {
  session_id: string;
  assistant_text: string;
  recommendations: RecommendationObject[];
  recommendation_action?: 'replace' | 'preserve';
  state: ChatState;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
}

export const sendChatMessage = async (params: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/chat', params);
  return response.data;
};

export const refreshRecommendations = async (sessionId: string): Promise<RefreshResponse> => {
  const response = await api.post<RefreshResponse>('/recommend_refresh', { session_id: sessionId });
  return response.data;
};
