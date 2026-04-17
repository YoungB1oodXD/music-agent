import { Song, Track } from '../types';

interface RecommendationRecord {
  display_score?: string | number | null;
  score?: number | null;
  similarity?: number | null;
  matchScore?: number | null;
  id?: string;
  track_id?: string;
  title?: string;
  name?: string;
  artist?: string;
  album?: string;
  coverUrl?: string;
  cover_url?: string;
  genre?: string;
  genre_description?: string;
  style?: string;
  duration?: number;
  durationSeconds?: number;
  tags?: string[];
  mood_tags?: string[];
  scene_tags?: string[];
  instrumentation?: string[];
  energy_note?: string;
  reason?: string;
  is_playable?: boolean;
  audio_url?: string;
  evidence?: {
    similarity?: number | null;
    hybrid_score?: number | null;
    cf_score?: number | null;
  };
}

function normalizeRecommendationScore(rec: RecommendationRecord, index: number, list: RecommendationRecord[]): number {
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

export const mapRecommendationsToTracks = (recommendations: (RecommendationRecord | Song)[]): Track[] => {
  if (!Array.isArray(recommendations)) {
    return [];
  }

  const DEFAULT_REASON = '基于您的听歌偏好推荐';
  const list = recommendations as RecommendationRecord[];

  return recommendations.map((rec, index) => {
    const id = (rec as RecommendationRecord).id || (rec as RecommendationRecord).track_id || `track-${index}`;
    let title = (rec as RecommendationRecord).title || (rec as RecommendationRecord).name || String(id);
    let artist = (rec as RecommendationRecord).artist || 'Unknown Artist';

    const recAny = rec as Record<string, unknown>;
    if (recAny.name && typeof recAny.name === 'string' && recAny.name.includes(' - ')) {
      const parts = recAny.name.split(' - ');
      artist = parts[0].trim();
      title = parts.slice(1).join(' - ').trim();
    }

    const genre = (rec as RecommendationRecord).genre || undefined;
    const style = (rec as RecommendationRecord).genre_description || (rec as RecommendationRecord).style || undefined;

    const allTags: string[] = [];
    const tags = (rec as RecommendationRecord).tags;
    if (Array.isArray(tags)) {
      allTags.push(...tags.filter((t: string) => !t.startsWith('doc:')));
    }
    const moodTags = (rec as RecommendationRecord).mood_tags;
    if (Array.isArray(moodTags)) {
      allTags.push(...moodTags);
    }
    const sceneTags = (rec as RecommendationRecord).scene_tags;
    if (Array.isArray(sceneTags)) {
      allTags.push(...sceneTags);
    }
    const instrumentation = (rec as RecommendationRecord).instrumentation;
    if (Array.isArray(instrumentation)) {
      allTags.push(...instrumentation);
    }
    const energyNote = (rec as RecommendationRecord).energy_note;
    if (energyNote) {
      allTags.push(energyNote);
    }
    const finalTags = allTags.slice(0, 4);

    const matchScore = normalizeRecommendationScore(rec as RecommendationRecord, index, list);

    const seedString = String(id) || `${title}-${artist}`.toLowerCase().replace(/\s+/g, '-');
    const coverUrl = (rec as RecommendationRecord).coverUrl || (rec as RecommendationRecord).cover_url ||
      `https://picsum.photos/seed/${encodeURIComponent(seedString)}/300/300`;

    return {
      id: String(id),
      title: title,
      artist: artist,
      album: (rec as RecommendationRecord).album || 'Unknown Album',
      coverUrl: coverUrl,
      tags: finalTags,
      genre: genre,
      style: style,
      duration: (rec as RecommendationRecord).duration || (rec as RecommendationRecord).durationSeconds || 0,
      matchScore: matchScore,
      reason: (rec as RecommendationRecord).reason || DEFAULT_REASON,
      recommendationReason: (rec as RecommendationRecord).reason || DEFAULT_REASON,
      isPlayable: (rec as RecommendationRecord).is_playable === true,
      audioUrl: (rec as RecommendationRecord).audio_url || undefined,
    };
  });
};
