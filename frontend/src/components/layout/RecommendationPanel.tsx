import React from 'react';
import { Play, Pause, Heart, ThumbsDown, Plus, Music, RefreshCw, TrendingUp } from 'lucide-react';
import { motion } from 'motion/react';
import { useChatStore } from '../../store/useChatStore';
import { usePlaylistStore } from '../../store/usePlaylistStore';
import { useAudioPlayer } from '../../contexts/AudioPlayerContext';
import { useToast } from './Toast';
import { Song } from '../../types';
import { formatDuration, cn } from '../../lib/utils';

export default function RecommendationPanel() {
  const { recommendations, toggleLike, sendFeedback } = useChatStore();
  const { playlists, addSongToPlaylist } = usePlaylistStore();
  const { playingTrackId, playTrack } = useAudioPlayer();
  const { showLike, showDislike, showRefresh, showAddToPlaylist } = useToast();

  const handleFeedback = async (type: 'like' | 'dislike' | 'refresh', song?: Song) => {
    if (type === 'like') {
      showLike(song?.title);
      await sendFeedback(song?.id || '', type);
    } else if (type === 'dislike') {
      showDislike(song?.title);
      await sendFeedback(song?.id || '', type);
    } else if (type === 'refresh') {
      showRefresh();
      await sendFeedback('all', type);
    }
  };

  const handleAddToPlaylist = async (pid: number | string, playlistName: string, song: Song) => {
    await addSongToPlaylist(String(pid), song);
    showAddToPlaylist(playlistName, song.title || song.id);
  };

  return (
    <aside className="w-96 shrink-0 bg-[#EBECE7] border-l border-gray-200 flex flex-col h-full overflow-hidden">
      <div className="p-6 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="text-[#1C1D1C] w-5 h-5" />
          <h2 className="font-bold text-[#1A1A1A]">推荐结果</h2>
        </div>
        <span className="text-[10px] bg-white text-gray-500 px-2 py-1 rounded uppercase font-bold tracking-wider border border-gray-200">
          {recommendations.length} 首歌曲
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {recommendations.length > 0 ? (
          recommendations.map((song, index) => (
            <SongCard 
              key={song.id} 
              song={song} 
              index={index}
              onLike={() => handleFeedback('like', song)}
              onFeedback={(type) => handleFeedback(type, song)}
              onAddToPlaylist={(pid, name) => handleAddToPlaylist(pid, name, song)}
              playlists={playlists}
              playingTrackId={playingTrackId}
              playTrack={playTrack}
            />
          ))
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
            <div className="w-16 h-16 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-400 shadow-sm">
              <Music size={32} />
            </div>
            <div>
              <p className="text-[#1A1A1A] font-medium">暂无推荐</p>
              <p className="text-xs text-gray-500 mt-1">在左侧对话框中描述你的音乐偏好，Melodia 将为你精准匹配。</p>
            </div>
          </div>
        )}
      </div>

      {recommendations.length > 0 && (
        <div className="p-4 bg-[#EBECE7] border-t border-gray-200">
          <button 
            onClick={() => handleFeedback('refresh')}
            className="w-full flex items-center justify-center gap-2 py-3 bg-white hover:bg-gray-50 text-[#1A1A1A] rounded-xl transition-all text-sm font-medium border border-gray-200 shadow-sm"
          >
            <RefreshCw size={16} />
            <span>换一批推荐</span>
          </button>
        </div>
      )}
    </aside>
  );
}

interface SongCardProps {
  song: Song;
  index: number;
  onLike: () => void | Promise<void>;
  onFeedback: (type: 'like' | 'dislike' | 'refresh') => void | Promise<void>;
  onAddToPlaylist: (pid: string, playlistName: string) => void | Promise<void>;
  playlists: any[];
  playingTrackId: string | null;
  playTrack: (id: string, url: string) => Promise<{ success: boolean; error?: string }>;
}

const SongCard: React.FC<SongCardProps> = ({ 
  song, 
  index, 
  onLike, 
  onFeedback,
  onAddToPlaylist,
  playlists,
  playingTrackId,
  playTrack,
}: SongCardProps & { playingTrackId: string | null; playTrack: (id: string, url: string) => Promise<{ success: boolean; error?: string }> }) => {
  const [isLiked, setIsLiked] = React.useState(false);
  const isThisPlaying = playingTrackId === song.id;
  const handlePlay = async () => {
    if (!song.audioUrl) {
      return;
    }
    const result = await playTrack(song.id, song.audioUrl);
    if (!result.success && result.error) {
      console.error('Play failed:', result.error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="group bg-white hover:bg-gray-50 border border-gray-100 hover:border-gray-300 rounded-2xl p-3 transition-all shadow-sm"
    >
      <div className="flex gap-3">
        <div className="relative w-16 h-16 shrink-0 rounded-lg overflow-hidden shadow-sm border border-gray-100">
          <img 
            src={song.coverUrl} 
            alt={song.title} 
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
            referrerPolicy="no-referrer"
          />
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <button 
              onClick={handlePlay}
              className="w-8 h-8 bg-[#D1E8C5] rounded-full flex items-center justify-center text-[#1C1D1C] shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-all duration-300"
            >
              {isThisPlaying ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" className="ml-0.5" />}
            </button>
          </div>
        </div>
        <div className="relative flex-1 min-w-0">
          <span className="absolute top-0 right-0 text-[10px] font-mono text-[#1C1D1C] bg-[#D1E8C5] px-1.5 py-0.5 rounded">
            {song.matchScore}%
          </span>
          {song.isPlayable && (
            <span className="inline-block text-[9px] font-bold text-white bg-emerald-500 px-1.5 py-0.5 rounded mb-1">
              可试听
            </span>
          )}
          <h3 className="text-sm font-bold text-[#1A1A1A] leading-snug break-words pr-16">{song.title}</h3>
          <p className="text-xs text-gray-500 truncate mt-0.5 pr-16">{song.artist}</p>
          {(song.genre || song.style) && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {song.genre && (
                <span className="text-[9px] font-medium text-white bg-[#5B8C5A] px-1.5 py-0.5 rounded">
                  {song.genre}
                </span>
              )}
              {song.style && song.style !== song.genre && (
                <span className="text-[9px] font-medium text-[#5B8C5A] bg-[#E8F5E2] border border-[#5B8C5A] px-1.5 py-0.5 rounded">
                  {song.style}
                </span>
              )}
            </div>
          )}
          <div className="flex flex-wrap gap-1 mt-2">
            {(song.tags || []).slice(0, 4).map(tag => (
              <span key={tag} className="text-[9px] text-gray-600 border border-gray-200 bg-gray-50 px-1.5 py-0.5 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button 
            onClick={() => {
              setIsLiked(!isLiked);
              onLike();
            }}
            className={cn(
              "p-1.5 rounded-lg transition-colors",
              isLiked ? "text-rose-500 bg-rose-50" : "text-gray-400 hover:text-rose-500 hover:bg-gray-100"
            )}
          >
            <Heart size={16} fill={isLiked ? "currentColor" : "none"} />
          </button>
          <button 
            onClick={() => onFeedback('dislike')}
            className="p-1.5 text-gray-400 hover:text-[#1A1A1A] hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ThumbsDown size={16} />
          </button>
          <div className="relative group/menu">
            <button className="p-1.5 text-gray-400 hover:text-[#1A1A1A] hover:bg-gray-100 rounded-lg transition-colors">
              <Plus size={16} />
            </button>
            <div className="absolute bottom-full left-0 mb-2 w-40 bg-white border border-gray-200 rounded-xl shadow-xl opacity-0 invisible group-hover/menu:opacity-100 group-hover/menu:visible transition-all z-20 p-1">
              <p className="px-3 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider">添加到歌单</p>
              {playlists.map(p => (
                <button 
                  key={p.id}
                  onClick={() => onAddToPlaylist(String(p.id), p.name)}
                  className="w-full text-left px-3 py-2 text-xs text-[#1A1A1A] hover:bg-gray-50 rounded-lg transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        </div>
        <span className="text-[10px] font-mono text-gray-400">{formatDuration(song.duration)}</span>
      </div>

      {song.recommendationReason && (
        <div className="mt-3 p-2.5 bg-[#F4F5F0] rounded-xl border border-gray-100/50">
          <p className="text-[11px] text-gray-600 leading-relaxed">
            <span className="font-bold text-[#1C1D1C] mr-1">AI 推荐理由：</span>
            {song.recommendationReason}
          </p>
        </div>
      )}
    </motion.div>
  );
}
