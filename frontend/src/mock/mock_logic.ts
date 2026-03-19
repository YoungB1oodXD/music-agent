import { SessionContext, Track } from '../types';
import { MOCK_TRACKS } from './mock_data';

export function getMockResponse(content: string): { context: SessionContext; tracks: Track[] } {
  if (content.toLowerCase().includes('drive') || content.includes('开车') || content.includes('夜晚')) {
    return {
      context: {
        mood: ['充满活力', '神秘'],
        scene: ['夜间驾驶', '城市漫游'],
        genre: ['合成器波', '电子乐'],
        energy: ['高能量', '节奏感强'],
        vocal: ['少量人声', '电子处理']
      },
      tracks: MOCK_TRACKS
    };
  } else {
    return {
      context: {
        mood: ['放松', '专注'],
        scene: ['工作', '学习'],
        genre: ['Lo-Fi', '环境音'],
        energy: ['低能量', '平缓'],
        vocal: ['纯音乐', '无人声']
      },
      tracks: [...MOCK_TRACKS].reverse().map(t => ({ ...t, matchScore: t.matchScore - 5 }))
    };
  }
}
