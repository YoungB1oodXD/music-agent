export const API_BASE = '/api';

export const ENDPOINTS = {
  HEALTH: `${API_BASE}/health`,
  CHAT: `${API_BASE}/chat`,
  FEEDBACK: `${API_BASE}/feedback`,
  SESSION_BASE: `${API_BASE}/session`,
  RESET_SESSION: `${API_BASE}/reset_session`,
} as const;
