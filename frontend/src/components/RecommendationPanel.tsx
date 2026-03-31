import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Play, BarChart2, ThumbsUp, ThumbsDown, RefreshCw, CheckCircle2, AlertCircle, X, Pause, Volume2 } from 'lucide-react';
import { Track } from '../types';
import { useAudioPlayer } from '../contexts/AudioPlayerContext';

interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'error';
  message: string;
}

interface RecommendationPanelProps {
  tracks: Track[];
  onFeedback: (message: string) => Promise<boolean>;
}

export function RecommendationPanel({ tracks, onFeedback }: RecommendationPanelProps) {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const showToast = (type: 'success' | 'info' | 'error', message: string) => {
    const id = Date.now().toString();
    setToast({ id, type, message });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    if (tracks.length > 0 && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [tracks]);

  return (
    <div className="w-[420px] flex-shrink-0 bg-slate-50/50 border-l border-gray-200 flex flex-col h-full shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.05)] z-10 relative">
      <div className="p-6 border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-10">
        <h2 className="font-display font-bold text-lg text-slate-900 flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-indigo-500" />
          推荐结果
        </h2>
        <p className="text-xs text-slate-500 mt-1 font-medium">基于当前会话上下文的混合推荐</p>
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`absolute top-20 left-4 right-4 z-20 p-3 rounded-lg shadow-lg flex items-center justify-between ${
              toast.type === 'success' ? 'bg-emerald-50 border border-emerald-200' :
              toast.type === 'error' ? 'bg-rose-50 border border-rose-200' :
              'bg-indigo-50 border border-indigo-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {toast.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : toast.type === 'error' ? (
                <AlertCircle className="w-4 h-4 text-rose-600" />
              ) : (
                <RefreshCw className="w-4 h-4 text-indigo-600" />
              )}
              <span className={`text-sm font-medium ${
                toast.type === 'success' ? 'text-emerald-700' :
                toast.type === 'error' ? 'text-rose-700' :
                'text-indigo-700'
              }`}>
                {toast.message}
              </span>
            </div>
            <button onClick={() => setToast(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence mode="popLayout">
          {tracks.map((track, idx) => (
            <TrackCard key={track.id} track={track} index={idx} onFeedback={onFeedback} showToast={showToast} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

interface TrackCardProps {
  track: Track;
  index: number;
  onFeedback: (message: string) => Promise<boolean>;
  showToast: (type: 'success' | 'info' | 'error', message: string) => void;
  key?: string | number;
}

function TrackCard({ track, index, onFeedback, showToast }: TrackCardProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [status, setStatus] = useState<'liked' | 'disliked' | 'refreshed' | 'error' | null>(null);
  const { playTrack, isPlaying } = useAudioPlayer();
  const playing = isPlaying(track.id);

  const handlePlayClick = async () => {
    if (!track.isPlayable || !track.audioUrl) return;
    const result = await playTrack(track.id, track.audioUrl);
    if (!result.success) {
      showToast('error', `播放失败: ${result.error || '未知错误'}`);
    }
  };

  const handleAction = async (action: 'like' | 'dislike' | 'refresh') => {
    if (loading) return;
    
    setLoading(action);
    setStatus(null);

    let message = '';
    if (action === 'like') message = `喜欢 id: ${track.id}`;
    else if (action === 'dislike') message = `不喜欢 id: ${track.id}`;
    else if (action === 'refresh') message = '换一批';

    const success = await onFeedback(message);
    
    setLoading(null);
    if (success) {
      if (action === 'like') {
        setStatus('liked');
        showToast('success', '已记录你的喜欢，后续会为你推荐更多类似的歌曲');
      } else if (action === 'dislike') {
        showToast('success', '已记录你的不喜欢，后续推荐将排除这首歌');
      } else if (action === 'refresh') {
        setStatus('refreshed');
        showToast('info', '已排除上一批结果，正在加载新的推荐');
      }
      
      setTimeout(() => setStatus(null), 2000);
    } else {
      setStatus('error');
      showToast('error', '请求失败，请稍后重试');
      setTimeout(() => setStatus(null), 3000);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20, height: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative bg-white border border-gray-200 hover:border-indigo-200 hover:shadow-md rounded-2xl p-4 transition-all overflow-hidden"
    >
      <div className="flex gap-4 items-start">
        <div className="relative w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 shadow-sm border border-gray-100">
          <img src={track.coverUrl} alt={track.title} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
          {track.isPlayable && track.audioUrl && (
            <>
              <div 
                onClick={handlePlayClick}
                className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
              >
                <div className="w-8 h-8 rounded-full bg-white/90 text-slate-900 flex items-center justify-center shadow-lg transform scale-75 group-hover:scale-100 transition-transform">
                  {playing ? (
                    <Pause className="w-4 h-4" fill="currentColor" />
                  ) : (
                    <Play className="w-4 h-4 ml-0.5" fill="currentColor" />
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <div className="truncate pr-2">
              <h4 className="text-sm font-bold text-slate-900 truncate">{track.title}</h4>
              <p className="text-xs text-slate-500 truncate mt-0.5">{track.artist}</p>
            </div>
            <div className="flex items-center gap-1 text-indigo-600 bg-indigo-50 px-2 py-1 rounded-md">
              <span className="text-xs font-bold">{track.matchScore}%</span>
            </div>
          </div>
          
          <div className="flex gap-1.5 mt-2.5 overflow-x-auto no-scrollbar items-center">
            {track.isPlayable && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-600 font-medium whitespace-nowrap border border-emerald-200 flex items-center gap-1">
                <Volume2 className="w-3 h-3" />
                可试听
              </span>
            )}
            {track.tags.slice(0, 3).map(tag => (
              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium whitespace-nowrap border border-slate-200">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
      
      <div className="mt-3.5 pt-3.5 border-t border-gray-100">
        <p className="text-xs text-slate-600 leading-relaxed">
          <span className="font-semibold text-slate-700 mr-1">推荐理由:</span>
          {track.reason}
        </p>
      </div>

      <div className="flex items-center gap-2 mt-3.5">
        <button 
          onClick={() => handleAction('like')}
          disabled={!!loading}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-colors text-xs font-medium border ${
            status === 'liked' 
              ? 'bg-emerald-50 text-emerald-600 border-emerald-200' 
              : 'bg-slate-50 hover:bg-emerald-50 text-slate-500 hover:text-emerald-600 border-transparent hover:border-emerald-200'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading === 'like' ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : status === 'liked' ? (
            <CheckCircle2 className="w-3.5 h-3.5" />
          ) : (
            <ThumbsUp className="w-3.5 h-3.5" />
          )}
          {status === 'liked' ? '已喜欢' : '喜欢'}
        </button>
        
        <button 
          onClick={() => handleAction('dislike')}
          disabled={!!loading}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-colors text-xs font-medium border ${
            status === 'disliked'
              ? 'bg-rose-50 text-rose-600 border-rose-200'
              : 'bg-slate-50 hover:bg-rose-50 text-slate-500 hover:text-rose-600 border-transparent hover:border-rose-200'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading === 'dislike' ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : status === 'disliked' ? (
            <CheckCircle2 className="w-3.5 h-3.5" />
          ) : (
            <ThumbsDown className="w-3.5 h-3.5" />
          )}
          {status === 'disliked' ? '已记录' : '不喜欢'}
        </button>

        <button 
          onClick={() => handleAction('refresh')}
          disabled={!!loading}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-colors text-xs font-medium border ${
            status === 'refreshed'
              ? 'bg-indigo-50 text-indigo-600 border-indigo-200'
              : 'bg-slate-50 hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 border-transparent hover:border-indigo-200'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading === 'refresh' ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          {status === 'refreshed' ? '已更新' : '换一批'}
        </button>
      </div>

      {status === 'error' && (
        <div className="mt-2 flex items-center justify-center gap-1.5 text-[10px] text-rose-500 font-medium">
          <AlertCircle className="w-3 h-3" />
          请求失败，请稍后重试
        </div>
      )}
      
      <div className="absolute bottom-0 left-0 h-1 bg-indigo-50 w-full">
        <motion.div 
          className="h-full bg-indigo-500"
          initial={{ width: 0 }}
          animate={{ width: `${track.matchScore}%` }}
          transition={{ duration: 1, delay: 0.5 + (index * 0.1) }}
        />
      </div>
    </motion.div>
  );
}
