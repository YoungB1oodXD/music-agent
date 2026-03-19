export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  coverUrl: string;
  tags: string[];
  matchScore: number;
  duration?: string;
  reason: string;
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
  debug: DebugInfo;
}
