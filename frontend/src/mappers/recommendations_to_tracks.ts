import { Track } from '../types';

export const mapRecommendationsToTracks = (recommendations: any): Track[] => {
  if (!Array.isArray(recommendations)) {
    return [];
  }

  const DEFAULT_REASON = '基于您的听歌偏好推荐';

  return recommendations.map((rec, index) => {
    if (typeof rec === 'string') {
      let title = rec;
      let artist = 'Unknown Artist';
      
      if (rec.includes(' - ')) {
        const parts = rec.split(' - ');
        artist = parts[0].trim();
        title = parts.slice(1).join(' - ').trim();
      }

      return {
        id: rec,
        title: title,
        artist: artist,
        album: 'Unknown Album',
        coverUrl: `https://picsum.photos/seed/${encodeURIComponent(rec)}/300/300`,
        tags: [],
        matchScore: 0,
        reason: DEFAULT_REASON,
      };
    }

    const id = rec.id || rec.track_id || `track-${index}`;
    let title = rec.title || rec.name || String(id);
    let artist = rec.artist || 'Unknown Artist';

    if (rec.name && typeof rec.name === 'string' && rec.name.includes(' - ')) {
      const parts = rec.name.split(' - ');
      artist = parts[0].trim();
      title = parts.slice(1).join(' - ').trim();
    }

    const tags = Array.isArray(rec.tags) 
      ? rec.tags.slice(0, 3).filter((t: string) => !t.startsWith('doc:'))
      : [];

    let matchScore = typeof rec.score === 'number' ? rec.score : (typeof rec.matchScore === 'number' ? rec.matchScore : 0);
    if (matchScore > 0 && matchScore <= 1) {
      matchScore = Math.round(matchScore * 100);
    }

    return {
      id: String(id),
      title: title,
      artist: artist,
      album: rec.album || 'Unknown Album',
      coverUrl: rec.coverUrl || `https://picsum.photos/seed/${encodeURIComponent(String(id))}/300/300`,
      tags: tags,
      matchScore: matchScore,
      reason: rec.reason || DEFAULT_REASON,
    };
  });
};
