import { SessionContext } from '../types';
import { ChatState } from '../services/chat';

export const mapChatStateToSessionContext = (state: ChatState): SessionContext => {
  const energyMap: Record<string, string> = {
    low: '低能量',
    medium: '中等能量',
    high: '高能量',
  };

  const vocalMap: Record<string, string> = {
    instrumental: '纯音乐',
    vocal: '有人声',
  };

  return {
    mood: state.mood ? [state.mood] : [],
    scene: state.scene ? [state.scene] : [],
    genre: state.genre ? [state.genre] : [],
    energy: state.preferred_energy && energyMap[state.preferred_energy] 
      ? [energyMap[state.preferred_energy]] 
      : [],
    vocal: state.preferred_vocals && vocalMap[state.preferred_vocals] 
      ? [vocalMap[state.preferred_vocals]] 
      : [],
  };
};
