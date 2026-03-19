import { FeedbackResponse } from '../types';
import { ENDPOINTS } from '../config/api';

export async function sendFeedback(params: {
  session_id: string;
  feedback_type: 'like' | 'dislike' | 'refresh';
  track_id: string;
  track_metadata?: Record<string, unknown>;
  recommendation_context?: Record<string, unknown>;
}): Promise<FeedbackResponse> {
  const response = await fetch(ENDPOINTS.FEEDBACK, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Feedback request failed: ${response.status}`);
  }

  return response.json();
}