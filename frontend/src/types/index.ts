export interface User {
  id: number;
  username: string;
  created_at: string;
  email?: string;
  avatar?: string;
}

export interface Song {
  id: string;
  track_id?: string;
  name?: string;
  title?: string;
  artist?: string;
  album?: string;
  coverUrl?: string;
  duration?: number; // in seconds
  matchScore?: number; // 0-100
  score?: number;
  tags?: string[];
  genre?: string; // 流派
  style?: string; // 风格
  reason?: string;
  recommendationReason?: string;
  isPlayable?: boolean;
  audioUrl?: string;
}

export type Track = Song & {
  genre?: string;
  style?: string;
};

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  timestamp: number | Date;
  recommendations?: Song[];
}

export interface Playlist {
  id: number | string;
  user_id: number;
  name: string;
  is_system: boolean;
  created_at: string;
  createdAt?: number | string; // for compatibility
  song_count: number;
  description?: string;
  songs?: Song[];
}

export interface SessionState {
  mood?: string;
  scene?: string;
  style?: string;
  energy?: string;
  vocal?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: Message[];
  sessionState: SessionState;
}

export interface SessionContext {
  mood: string[];
  scene: string[];
  genre: string[];
  energy: string[];
  vocal: string[];
}

export interface DebugInfo {
  llm_enabled: boolean;
  llm_provider: string;
  llm_model: string;
  llm_called: boolean;
  fallback_used: boolean;
  llm_latency_ms: number;
}

export interface FeedbackResponse {
  success: boolean;
  ack_message: string;
  updated_preference_state: Record<string, unknown>;
  next_strategy: Record<string, unknown>;
  recommendations: Song[];
  debug: DebugInfo;
}

export interface RefreshResponse {
  session_id: string;
  recommendations: Song[];
  state: SessionState;
  debug: DebugInfo;
}
