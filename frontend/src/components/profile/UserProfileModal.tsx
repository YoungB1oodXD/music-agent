import React, { useEffect } from 'react';
import { useProfileStore } from '../../store/useProfileStore';
import { useAuthStore } from '../../store/useAuthStore';
import { RefreshCw, X, Sparkles, Headphones, Hash, ThumbsUp, ThumbsDown } from 'lucide-react';

interface UserProfileModalProps {
  onClose: () => void;
}

// Subcomponents
const PortraitCard: React.FC<{
  children: React.ReactNode;
  title?: string;
  icon?: React.ReactNode;
  className?: string;
}> = ({ children, title, icon, className = '' }) => (
  <div
    className={`bg-white border border-stone-200/60 rounded-3xl p-6 md:p-8 shadow-sm hover:shadow-md transition-shadow ${className}`}
  >
    {title && (
      <div className="flex items-center gap-2 mb-6">
        {icon && (
          <span className="flex items-center justify-center w-8 h-8 rounded-xl bg-[#F4F5F0] text-[#1C1D1C] border border-stone-200">
            {icon}
          </span>
        )}
        <h3 className="text-[#1C1D1C] font-black text-lg tracking-tight">{title}</h3>
      </div>
    )}
    {children}
  </div>
);

const GenreProgressBar: React.FC<{
  genre: string;
  count: number;
  maxCount: number;
  type: 'like' | 'dislike';
}> = ({ genre, count, maxCount, type }) => {
  const percentage = Math.max((count / maxCount) * 100, 5);
  const colorClass = type === 'like' ? 'bg-[#D1E8C5]' : 'bg-rose-100';

  return (
    <div className="flex items-center gap-4 mb-4 last:mb-0 group">
      <div className="w-28 text-sm font-bold text-stone-600 group-hover:text-[#1C1D1C] transition-colors truncate">
        {genre}
      </div>
      <div className="flex-1 h-6 bg-stone-100 rounded-xl overflow-hidden relative border border-stone-200/50">
        <div
          className={`absolute top-0 left-0 h-full ${colorClass} rounded-xl transition-all duration-1000 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div
        className={`w-12 text-right text-sm font-black ${
          type === 'like' ? 'text-[#1C1D1C]' : 'text-rose-400'
        }`}
      >
        {count}次
      </div>
    </div>
  );
};

const KeywordPill: React.FC<{ keyword: string }> = ({ keyword }) => (
  <span className="inline-block px-3 py-1.5 bg-[#D1E8C5] text-[#1C1D1C] rounded-lg text-xs font-bold border border-[#b5d3a5] hover:bg-[#b0d09e] transition-all cursor-default shadow-sm">
    {keyword}
  </span>
);

const SceneTag: React.FC<{ scene: string }> = ({ scene }) => (
  <span className="inline-block bg-white text-[#1C1D1C] px-3 py-1.5 rounded-lg text-xs font-bold cursor-default border border-stone-200 shadow-sm hover:border-[#1C1D1C] transition-colors">
    {scene}
  </span>
);

const LoadingSkeleton = () => (
  <div className="space-y-6 animate-pulse p-6">
    <div className="bg-gray-200 h-6 w-3/4 rounded-md mb-2" />
    <div className="bg-gray-200 h-6 w-1/2 rounded-md mb-8" />
    <div className="flex gap-4">
      <div className="bg-gray-200 h-8 w-24 rounded-lg" />
      <div className="bg-gray-200 h-8 w-32 rounded-lg" />
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-gray-200 h-48 rounded-xl" />
      <div className="bg-gray-200 h-48 rounded-xl" />
    </div>
  </div>
);

export default function UserProfileModal({ onClose }: UserProfileModalProps) {
  const { user } = useAuthStore();
  const { preferences, fetchProfile, isLoading, clearPreferences } = useProfileStore();

  useEffect(() => {
    if (user?.id) {
      fetchProfile(user.id);
    }
  }, [user?.id, fetchProfile]);

  if (!preferences && !isLoading) {
    return null;
  }

  const maxLikedCount = preferences
    ? Math.max(...(Object.values(preferences.liked_genre_counts) as number[]), 1)
    : 1;
  const maxDislikedCount = preferences
    ? Math.max(...(Object.values(preferences.disliked_genre_counts) as number[]), 1)
    : 1;

  const scenesList = preferences?.scene
    ? preferences.scene.split('/').map((s) => s.trim())
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Background overlay */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal Container */}
      <div className="bg-[#F4F5F0] rounded-[2rem] w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl relative z-10 animate-in slide-in-from-bottom-4 duration-200 border border-stone-200">
        {/* Header */}
        <div className="sticky top-0 bg-[#F4F5F0]/90 backdrop-blur-md border-b border-stone-200 p-6 flex items-center justify-between z-20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1C1D1C] text-[#D1E8C5] shadow-lg flex items-center justify-center font-black text-xl">
              {user?.username?.charAt(0).toUpperCase() || '✨'}
            </div>
            <div>
              <h2 className="text-xl font-black text-[#1C1D1C] tracking-tight leading-none mb-1">
                我的音乐画像
              </h2>
              <p className="text-xs font-bold text-stone-500">Mustify AI 独家生成</p>
            </div>
          </div>
          <div className="flex gap-3 items-center">
            <button
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-[#1C1D1C] hover:bg-stone-50 hover:shadow-sm transition-all text-sm font-bold active:scale-95"
              title="清除当前画像并重新生成"
              onClick={() => user && clearPreferences(user.id)}
              disabled={isLoading}
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              清除画像
            </button>
            <button
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center rounded-xl bg-white text-stone-400 hover:text-[#1C1D1C] border border-stone-200 hover:bg-stone-50 transition-all active:scale-95 shadow-sm"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div>
          {isLoading && !preferences ? (
            <LoadingSkeleton />
          ) : preferences ? (
            <div className="p-6 md:p-8 space-y-6">
              {/* Core Portrait Summary */}
              <div className="bg-[#1C1D1C] rounded-3xl p-8 shadow-xl relative overflow-hidden">
                <Sparkles className="absolute -top-4 -right-4 text-white/5 w-40 h-40 rotate-12 pointer-events-none" />

                <div className="relative z-10">
                  <div className="inline-flex gap-2 items-center bg-[#D1E8C5] text-[#1C1D1C] px-3 py-1.5 rounded-full text-xs font-black uppercase tracking-widest mb-6 shadow-sm">
                    <Sparkles size={14} />
                    <span>Mustify AI 深度解析</span>
                  </div>

                  <p className="text-[#F4F5F0] text-lg md:text-xl leading-relaxed font-medium tracking-wide">
                    {preferences.deep_analysis || preferences.summary}
                  </p>
                </div>
              </div>

              {/* Scenes and Keywords */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <PortraitCard title="适宜场景" icon={<Headphones size={16} />} className="mb-0">
                  <div className="flex flex-wrap gap-2">
                    {scenesList.map((scene, idx) => (
                      <SceneTag key={idx} scene={scene} />
                    ))}
                  </div>
                </PortraitCard>

                <PortraitCard title="音乐指纹" icon={<Hash size={16} />} className="mb-0">
                  <div className="flex flex-wrap gap-2">
                    {preferences.keywords?.map((keyword) => (
                      <KeywordPill key={keyword} keyword={keyword} />
                    ))}
                  </div>
                </PortraitCard>
              </div>

              {/* Stats Breakdown */}
              <div className="flex flex-col gap-6">
                <PortraitCard title="心动偏好" icon={<ThumbsUp size={16} />} className="mb-0">
                  {preferences.liked_genres.length === 0 ? (
                    <p className="text-gray-400 text-sm font-medium">暂无数据，多听听歌吧</p>
                  ) : (
                    <div className="space-y-4">
                      {preferences.liked_genres.map((genre) => (
                        <GenreProgressBar
                          key={genre}
                          genre={genre}
                          count={preferences.liked_genre_counts[genre] || 1}
                          maxCount={maxLikedCount}
                          type="like"
                        />
                      ))}
                    </div>
                  )}
                </PortraitCard>

                <PortraitCard title="风格避雷" icon={<ThumbsDown size={16} />} className="mb-0">
                  {preferences.disliked_genres.length === 0 ? (
                    <p className="text-gray-400 text-sm font-medium">好像你什么风格都能接受？</p>
                  ) : (
                    <div className="space-y-4">
                      {preferences.disliked_genres.map((genre) => (
                        <GenreProgressBar
                          key={genre}
                          genre={genre}
                          count={preferences.disliked_genre_counts[genre] || 1}
                          maxCount={maxDislikedCount}
                          type="dislike"
                        />
                      ))}
                    </div>
                  )}
                </PortraitCard>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Buffering/Loading AI Overlay */}
      {isLoading && preferences && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 backdrop-blur-sm animate-in fade-in duration-200 p-4">
          <div className="bg-white p-8 md:p-10 rounded-[2rem] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] flex flex-col items-center border border-stone-200/50 animate-in zoom-in-95 duration-300 text-center max-w-sm w-full">
            <div className="w-16 h-16 bg-[#1C1D1C] rounded-2xl flex items-center justify-center text-[#D1E8C5] mb-6 shadow-xl relative">
              <div className="absolute inset-0 bg-[#D1E8C5] blur-xl opacity-20 rounded-2xl animate-pulse" />
              <Sparkles size={32} className="animate-pulse" />
            </div>
            <h3 className="text-[#1C1D1C] text-xl font-black mb-2 tracking-tight">
              Mustify AI 分析中
            </h3>
            <p className="text-stone-500 text-sm font-bold leading-relaxed">
              正在提取您的音乐指纹
              <br />
              并生成最新画像...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}