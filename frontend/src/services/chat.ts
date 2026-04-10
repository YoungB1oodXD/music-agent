import { ENDPOINTS } from '../config/api';
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
  const response = await fetch(ENDPOINTS.CHAT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Chat API error: ${response.status}`);
  }

  try {
    const data = await response.json();
    return data as ChatResponse;
  } catch (error) {
    throw new Error('Failed to parse chat response');
  }
};

export const refreshRecommendations = async (sessionId: string): Promise<RefreshResponse> => {
  const response = await fetch(ENDPOINTS.RECOMMEND_REFRESH, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Refresh API error: ${response.status}`);
  }

  try {
    const data = await response.json();
    return data as RefreshResponse;
  } catch {
    throw new Error('Failed to parse refresh response');
  }
};
