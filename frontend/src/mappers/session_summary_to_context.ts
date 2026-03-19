import { SessionContext } from '../types';

export function mapSessionSummaryToSessionContext(state: any): SessionContext {
  const context: SessionContext = {
    mood: [],
    scene: [],
    genre: [],
    energy: [],
    vocal: [],
  };

  if (!state || typeof state !== 'object') {
    return context;
  }

  if (typeof state.mood === 'string' && state.mood.trim()) {
    context.mood = [state.mood.trim()];
  }

  if (typeof state.scene === 'string' && state.scene.trim()) {
    context.scene = [state.scene.trim()];
  }

  if (typeof state.genre === 'string' && state.genre.trim()) {
    context.genre = [state.genre.trim()];
  }

  const profile = state.preference_profile;
  if (profile && typeof profile === 'object') {
    const energyMap: Record<string, string> = {
      low: '低能量',
      medium: '中等能量',
      high: '高能量',
    };

    const vocalMap: Record<string, string> = {
      instrumental: '纯音乐',
      vocal: '有人声',
    };

    const energy = profile.preferred_energy;
    if (typeof energy === 'string' && energyMap[energy]) {
      context.energy = [energyMap[energy]];
    }

    const vocals = profile.preferred_vocals;
    if (typeof vocals === 'string' && vocalMap[vocals]) {
      context.vocal = [vocalMap[vocals]];
    }
  }

  return context;
}
