import { ENDPOINTS } from '../config/api';

export interface HealthStatus {
  status?: string;
  llm_mode?: string;
  raw: unknown;
}

export const fetchHealth = async (): Promise<HealthStatus> => {
  try {
    const response = await fetch(ENDPOINTS.HEALTH);
    if (!response.ok) {
      return {
        status: 'error',
        raw: `HTTP error! status: ${response.status}`,
      };
    }
    const data = await response.json();
    return {
      status: data.status,
      llm_mode: data.llm_mode,
      raw: data,
    };
  } catch (error) {
    return {
      status: 'error',
      raw: error instanceof Error ? error.message : String(error),
    };
  }
};
