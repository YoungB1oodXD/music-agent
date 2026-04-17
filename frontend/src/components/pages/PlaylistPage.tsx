import React, { useEffect, useState } from 'react';
import { ListMusic, Play, Trash2, Clock, Music, Calendar } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePlaylistStore } from '../../store/usePlaylistStore';
import { useAudioPlayer } from '../../contexts/AudioPlayerContext';
import { formatDuration } from '../../lib/utils';
import api from '../../services/api';
import { Song } from '../../types';

export default function PlaylistPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { playlists, removeSongFromPlaylist, deletePlaylist } = usePlaylistStore();
  const { playingTrackId, playTrack } = useAudioPlayer();
  const [playlistSongs, setPlaylistSongs] = useState<Song[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const playlist = playlists.find(p => String(p.id) === String(id));

  useEffect(() => {
    if (id) {
      setIsLoading(true);
      setFetchError(null);
      api.get(`/playlists/${id}`)
        .then(res => {
          setPlaylistSongs(res.data.songs || []);
          setIsLoading(false);
        })
        .catch((err: Error) => {
          setFetchError(err.message || '加载失败');
          setIsLoading(false);
        });
    }
  }, [id]);

  if (!playlist) {
    return (
      <main className="flex-1 flex flex-col bg-[#F4F5F0] items-center justify-center text-gray-500">
        <ListMusic size={48} className="mb-4 opacity-20" />
        <p>歌单不存在或已被删除</p>
      </main>
    );
  }

  const handleDeletePlaylist = () => {
    if (window.confirm('确定要删除这个歌单吗？')) {
      deletePlaylist(String(playlist.id));
      navigate('/');
    }
  };

  return (
    <main className="flex-1 flex flex-col bg-[#F4F5F0] relative overflow-hidden">
      {/* Header */}
      <header className="h-64 bg-[#1C1D1C] text-white p-8 flex items-end relative overflow-hidden shrink-0">
        <div className="absolute inset-0 opacity-10 bg-[url('https://picsum.photos/seed/music/1000/400')] bg-cover bg-center blur-sm" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1C1D1C] to-transparent" />
        
        <div className="relative z-10 flex items-end gap-6 w-full max-w-5xl mx-auto">
          <div className="w-48 h-48 bg-[#282928] rounded-2xl shadow-2xl flex items-center justify-center border border-[#383938] shrink-0 overflow-hidden">
            {playlistSongs.length > 0 ? (
              <img src={(playlistSongs[0] as any).cover_url || playlistSongs[0].coverUrl || `https://via.placeholder.com/300x300/6366f1/ffffff?text=${encodeURIComponent((playlistSongs[0].title || 'M').substring(0, 10))}`} alt="Cover" className="w-full h-full object-cover" />
            ) : (
              <Music size={48} className="text-[#D1E8C5] opacity-50" />
            )}
          </div>
          
          <div className="flex-1 pb-2">
            <p className="text-xs font-bold text-[#D1E8C5] uppercase tracking-widest mb-2">歌单</p>
            <h1 className="text-5xl font-bold tracking-tight mb-4">{playlist.name}</h1>
            {playlist.description && (
              <p className="text-stone-400 text-sm mb-4">{playlist.description}</p>
            )}
            <div className="flex items-center gap-4 text-xs text-stone-400 font-medium">
              <div className="flex items-center gap-1">
                <Music size={14} />
                <span>{playlistSongs.length} 首歌</span>
              </div>
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                <span>创建于 {new Date(playlist.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Action Bar */}
      <div className="px-8 py-6 max-w-5xl mx-auto w-full flex items-center justify-between shrink-0">
        <button 
          onClick={() => {
            const firstSong = playlistSongs[0];
            const audioUrl = (firstSong as any).audio_url || firstSong.audioUrl;
            if (audioUrl) {
              playTrack(String(firstSong.track_id || firstSong.id), audioUrl);
            }
          }}
          className="w-14 h-14 bg-[#D1E8C5] hover:bg-[#bfe0ae] hover:scale-105 text-[#1C1D1C] rounded-full flex items-center justify-center shadow-lg transition-all"
        >
          <Play size={24} fill="currentColor" className="ml-1" />
        </button>
        <button 
          onClick={handleDeletePlaylist}
          className="text-gray-400 hover:text-rose-500 flex items-center gap-2 text-sm font-medium transition-colors px-4 py-2 rounded-lg hover:bg-rose-50"
        >
          <Trash2 size={16} />
          <span>删除歌单</span>
        </button>
      </div>

      {fetchError && (
        <div className="px-8 py-4 bg-red-50 border-b border-red-100 text-red-600 text-sm">
          {fetchError}
        </div>
      )}

      {/* Song List */}
      <div className="flex-1 overflow-y-auto px-8 pb-8">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-[auto_1fr_1fr_auto_auto] gap-4 px-4 py-2 border-b border-gray-200 text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">
            <div className="w-8 text-center">#</div>
            <div>标题</div>
            <div>专辑</div>
            <div className="w-16 text-center"><Clock size={14} className="mx-auto" /></div>
            <div className="w-10"></div>
          </div>

          <div className="space-y-1">
              {playlistSongs.length === 0 && !isLoading ? (
                <div className="text-center py-12 text-gray-500">
                  <p>歌单还是空的，去发现一些好音乐吧！</p>
                </div>
              ) : (
                playlistSongs.map((song, index) => (
                <div 
                  key={`${song.id || song.track_id}-${index}`}
                  className="grid grid-cols-[auto_1fr_1fr_auto_auto] gap-4 items-center px-4 py-3 hover:bg-white rounded-xl transition-colors group border border-transparent hover:border-gray-200 hover:shadow-sm"
                >
                  <div className="w-8 text-center text-sm text-gray-400 font-mono">{index + 1}</div>
                  <div className="flex items-center gap-3 min-w-0">
                    <img src={(song as any).cover_url || song.coverUrl || `https://via.placeholder.com/300x300/6366f1/ffffff?text=${encodeURIComponent((song.title || song.track_id || 'M').substring(0, 2))}`} alt={song.title || song.track_id || ''} className="w-10 h-10 rounded shadow-sm object-cover" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-bold text-[#1A1A1A] truncate">{song.title || song.track_id || 'Unknown'}</p>
                        {(song as any).is_playable && (
                          <span className="text-[9px] font-bold text-white bg-emerald-500 px-1.5 py-0.5 rounded animate-pulse shrink-0">可试听</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 truncate">{song.artist || '-'}</p>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500 truncate">{song.album || '-'}</div>
                  <div className="w-16 text-center text-sm font-mono text-gray-400">{song.duration ? formatDuration(song.duration) : '-'}</div>
                  <div className="w-10 text-right">
                    <button
                      onClick={async () => {
                        const trackId = String(song.track_id || song.id);
                        const updatedSongs = await removeSongFromPlaylist(String(playlist.id), trackId);
                        setPlaylistSongs(updatedSongs);
                      }}
                      className="p-2 text-gray-400 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-all rounded-lg hover:bg-rose-50"
                      title="从歌单移除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
