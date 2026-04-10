import api from './api';
import { ENDPOINTS } from '../config/api';

export interface SessionResponse {
  ok: boolean;
  session_id?: string;
  state?: unknown;
  notFound?: boolean;
}

export const fetchSession = async (sessionId: string): Promise<SessionResponse> => {
  const response = await fetch(`${ENDPOINTS.SESSION_BASE}/${encodeURIComponent(sessionId)}`);
  
  if (response.status === 404) {
    return { ok: false, notFound: true };
  }
  
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.status}`);
  }
  
  try {
    const data = await response.json();
    return { ok: true, ...data };
  } catch (error) {
    throw new Error('Failed to parse session response');
  }
};

export const resetSession = async (sessionId: string): Promise<{ ok: boolean }> => {
  const response = await api.post(ENDPOINTS.RESET_SESSION, { session_id: sessionId });
  return response.data;
};
