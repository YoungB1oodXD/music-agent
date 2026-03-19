import { Message, Track } from '../types';

export const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'agent',
    content: '你好！我是音乐推荐 Agent。今天想听点什么？你可以描述你的心情、正在做的事情，或者直接告诉我你喜欢的歌手和风格。',
    timestamp: new Date(Date.now() - 60000)
  }
];

export const MOCK_TRACKS: Track[] = [
  {
    id: 't1',
    title: 'Midnight City',
    artist: 'M83',
    album: 'Hurry Up, We\'re Dreaming',
    coverUrl: 'https://picsum.photos/seed/midnight/300/300',
    tags: ['Synthwave', 'Indie Pop', 'Night'],
    matchScore: 98,
    reason: '强烈的合成器节拍与你要求的"夜晚驾驶"场景完美契合，能量感十足。'
  },
  {
    id: 't2',
    title: 'Nightcall',
    artist: 'Kavinsky',
    album: 'OutRun',
    coverUrl: 'https://picsum.photos/seed/nightcall/300/300',
    tags: ['Retrowave', 'Driving', 'Dark'],
    matchScore: 94,
    reason: '经典的复古电子乐，低沉的人声处理营造出神秘的夜晚氛围。'
  },
  {
    id: 't3',
    title: 'Resonance',
    artist: 'HOME',
    album: 'Odyssey',
    coverUrl: 'https://picsum.photos/seed/resonance/300/300',
    tags: ['Chillwave', 'Nostalgic', 'Electronic'],
    matchScore: 89,
    reason: '带有怀旧感的电子旋律，适合在放松或专注时作为背景音乐。'
  },
  {
    id: 't4',
    title: 'The Perfect Girl',
    artist: 'Mareux',
    album: 'The Perfect Girl',
    coverUrl: 'https://picsum.photos/seed/perfect/300/300',
    tags: ['Darkwave', 'Post-Punk', 'Moody'],
    matchScore: 85,
    reason: '暗黑波风格，节奏感强且带有一丝忧郁，符合你偏好的冷色调情绪。'
  },
  {
    id: 't5',
    title: 'After Dark',
    artist: 'Mr.Kitty',
    album: 'Time',
    coverUrl: 'https://picsum.photos/seed/afterdark/300/300',
    tags: ['Synthpop', 'Alternative', 'Upbeat'],
    matchScore: 78,
    reason: '轻快的合成器流行乐，人声空灵，能有效提升当前的能量水平。'
  }
];
