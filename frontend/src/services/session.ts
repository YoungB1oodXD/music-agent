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
  const response = await fetch(ENDPOINTS.RESET_SESSION, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to reset session: ${response.status}`);
  }
  
  try {
    return await response.json();
  } catch (error) {
    throw new Error('Failed to parse reset session response');
  }
};
