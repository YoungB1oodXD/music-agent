import { Track } from '../types';

function normalizeRecommendationScore(rec: any, index: number, list: any[]): number {
  // Priority 1: Use backend-calibrated display_score
  if (rec.display_score !== null && rec.display_score !== undefined) {
    const displayScore = typeof rec.display_score === 'string' 
      ? parseInt(rec.display_score, 10) 
      : Number(rec.display_score);
    if (!isNaN(displayScore) && displayScore >= 0 && displayScore <= 100) {
      return displayScore;
    }
  }
  
  // Priority 2: Try multiple raw score fields from backend
  const rawScore = rec.score ?? rec.similarity ?? rec.matchScore ?? 
                   rec.evidence?.similarity ?? rec.evidence?.hybrid_score ?? 
                   rec.evidence?.cf_score ?? null;
  
  if (rawScore === null || rawScore === undefined) {
    // Fallback: relative position-based score
    if (list.length <= 1) return 90;
    const positionBonus = Math.round((1 - index / list.length) * 15);
    return Math.min(95, 80 + positionBonus);
  }
  
  const numScore = typeof rawScore === 'string' ? parseFloat(rawScore) : Number(rawScore);
  
  if (isNaN(numScore)) return 80;
  
  // If score is in 0-1 range, convert to display-friendly range (70-95)
  if (numScore > 0 && numScore <= 1) {
    // Map 0.26-1.0 to 70-95 (typical similarity range)
    const normalized = (numScore - 0.26) / (1.0 - 0.26);
    return Math.round(70 + normalized * 25);
  }
  
  // If score is already in 0-100 range
  if (numScore > 0 && numScore <= 100) {
    return Math.round(numScore);
  }
  
  // Clamp out-of-range values
  if (numScore <= 0) return 70;
  return Math.min(98, Math.round(numScore));
}

export const mapRecommendationsToTracks = (recommendations: any): Track[] => {
  if (!Array.isArray(recommendations)) {
    return [];
  }

  const DEFAULT_REASON = '基于您的听歌偏好推荐';
  const list = recommendations;

  return list.map((rec, index) => {
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
        matchScore: normalizeRecommendationScore(rec, index, list),
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

    const matchScore = normalizeRecommendationScore(rec, index, list);

    if (process.env.NODE_ENV === 'development') {
      console.log(`[Track ${id}] display_score: ${rec.display_score}, raw_score: ${rec.score} -> matchScore: ${matchScore}`);
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
      isPlayable: rec.is_playable === true,
      audioUrl: rec.audio_url || undefined,
    };
  });
};
