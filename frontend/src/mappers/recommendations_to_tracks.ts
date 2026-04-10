import { Track } from '../types';

function normalizeRecommendationScore(rec: any, index: number, list: any[]): number {
  if (rec.display_score !== null && rec.display_score !== undefined) {
    const displayScore = typeof rec.display_score === 'string' 
      ? parseInt(rec.display_score, 10) 
      : Number(rec.display_score);
    if (!isNaN(displayScore) && displayScore >= 0 && displayScore <= 100) {
      return displayScore;
    }
  }
  
  const rawScore = rec.score ?? rec.similarity ?? rec.matchScore ?? 
                   rec.evidence?.similarity ?? rec.evidence?.hybrid_score ?? 
                   rec.evidence?.cf_score ?? null;
  
  if (rawScore === null || rawScore === undefined) {
    if (list.length <= 1) return 90;
    const positionBonus = Math.round((1 - index / list.length) * 15);
    return Math.min(95, 80 + positionBonus);
  }
  
  const numScore = typeof rawScore === 'string' ? parseFloat(rawScore) : Number(rawScore);
  
  if (isNaN(numScore)) return 80;
  
  if (numScore > 0 && numScore <= 1) {
    const normalized = (numScore - 0.26) / (1.0 - 0.26);
    return Math.round(70 + normalized * 25);
  }
  
  if (numScore > 0 && numScore <= 100) {
    return Math.round(numScore);
  }
  
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

      const seedString = rec.toLowerCase().replace(/\s+/g, '-');
      return {
        id: rec,
        title: title,
        artist: artist,
        album: 'Unknown Album',
        coverUrl: `https://picsum.photos/seed/${encodeURIComponent(seedString)}/300/300`,
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

    const genre = rec.genre || undefined;
    const style = rec.genre_description || rec.style || undefined;

    const allTags: string[] = [];
    if (Array.isArray(rec.tags)) {
      allTags.push(...rec.tags.filter((t: string) => !t.startsWith('doc:')));
    }
    if (Array.isArray(rec.mood_tags)) {
      allTags.push(...rec.mood_tags);
    }
    if (Array.isArray(rec.scene_tags)) {
      allTags.push(...rec.scene_tags);
    }
    if (Array.isArray(rec.instrumentation)) {
      allTags.push(...rec.instrumentation);
    }
    if (rec.energy_note) {
      allTags.push(rec.energy_note);
    }
    const tags = allTags.slice(0, 4);

    const matchScore = normalizeRecommendationScore(rec, index, list);

    const seedString = String(id) || `${title}-${artist}`.toLowerCase().replace(/\s+/g, '-');
    const coverUrl = rec.coverUrl || rec.cover_url || 
      `https://picsum.photos/seed/${encodeURIComponent(seedString)}/300/300`;

    return {
      id: String(id),
      title: title,
      artist: artist,
      album: rec.album || 'Unknown Album',
      coverUrl: coverUrl,
      tags: tags,
      genre: genre,
      style: style,
      duration: rec.duration || rec.durationSeconds || 0,
      matchScore: matchScore,
      reason: rec.reason || DEFAULT_REASON,
      recommendationReason: rec.reason || DEFAULT_REASON,
      isPlayable: rec.is_playable === true,
      audioUrl: rec.audio_url || undefined,
    };
  });
};
