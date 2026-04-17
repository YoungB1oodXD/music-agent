import api from '../services/api';
import { FeedbackResponse } from '../types';

export async function sendFeedback(params: {
  session_id: string;
  feedback_type: 'like' | 'dislike' | 'refresh';
  track_id: string;
  track_metadata?: Record<string, unknown>;
  recommendation_context?: Record<string, unknown>;
}): Promise<FeedbackResponse> {
  const response = await api.post<FeedbackResponse>('/feedback', params);
  return response.data;
}
