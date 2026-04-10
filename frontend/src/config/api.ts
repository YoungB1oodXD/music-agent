export const API_BASE = '/api';

export const ENDPOINTS = {
  HEALTH: `${API_BASE}/health`,
  CHAT: `${API_BASE}/chat`,
  FEEDBACK: `${API_BASE}/feedback`,
  RECOMMEND_REFRESH: `${API_BASE}/recommend/refresh`,
  SESSION_BASE: `${API_BASE}/sessions`,
  RESET_SESSION: `${API_BASE}/reset_session`,
} as const;
