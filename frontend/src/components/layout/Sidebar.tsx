import React, { useState, useEffect } from 'react';
import { 
  Music, 
  ListMusic, 
  History, 
  Settings, 
  LogOut, 
  Plus,
  LayoutDashboard,
  User as UserIcon,
  Tag
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';
import { usePlaylistStore } from '../../store/usePlaylistStore';
import { useChatStore } from '../../store/useChatStore';
import { cn } from '../../lib/utils';
import UserProfileModal from '../profile/UserProfileModal';

export default function Sidebar() {
  const { user, logout, isAuthenticated } = useAuthStore();
  const { playlists, fetchPlaylists, createPlaylist, isCreating, error } = usePlaylistStore();
  const { sessionState } = useChatStore();
  const navigate = useNavigate();
  const location = useLocation();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [newPlaylistDesc, setNewPlaylistDesc] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      fetchPlaylists();
    }
  }, [isAuthenticated]);

  const handleCreatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPlaylistName.trim() && !isCreating) {
      const success = await createPlaylist(newPlaylistName.trim());
      if (success) {
        setIsModalOpen(false);
        setNewPlaylistName('');
        setNewPlaylistDesc('');
      }
    }
  };

  return (
    <>
      <aside className="w-64 bg-[#1C1D1C] border-r border-[#282928] flex flex-col h-full text-stone-300 shrink-0">
        <div className="p-4 m-3 bg-[#282928] rounded-2xl flex items-center gap-3 cursor-pointer shadow-sm border border-[#383938]" onClick={() => navigate('/')}>
          <div className="w-10 h-10 bg-[#D1E8C5] rounded-xl flex items-center justify-center shadow-inner shrink-0">
            <Music className="text-[#1C1D1C] w-6 h-6" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-xl font-black text-white tracking-tight leading-none mb-1">Mustify</h1>
            <span className="text-[9px] text-[#D1E8C5] font-mono tracking-widest uppercase opacity-80 leading-none">AI Music Engine</span>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto mt-2">
          <div className="pb-4">
            <p className="px-2 text-sm font-semibold text-stone-500 uppercase tracking-wider mb-2">
              主菜单
            </p>
            <NavItem 
              icon={<LayoutDashboard size={20} />} 
              label="发现音乐" 
              active={location.pathname === '/'} 
              onClick={() => navigate('/')}
            />
            <NavItem 
              icon={<History size={20} />} 
              label="最近对话" 
              active={location.pathname === '/history'}
              onClick={() => navigate('/history')}
            />
            <NavItem
              icon={<UserIcon size={20} />}
              label="我的画像"
              active={isProfileModalOpen}
              onClick={() => setIsProfileModalOpen(true)}
            />
          </div>

          <div className="pt-4 border-t border-[#282928] pb-4">
            <p className="px-2 text-sm font-semibold text-stone-500 uppercase tracking-wider mb-2">
              当前偏好
            </p>
            <div className="px-2 flex flex-wrap gap-2">
              {Object.entries(sessionState).map(([key, value]) => {
                if (!value || value === '未知') return null;
                return (
                  <div key={key} className="flex items-center gap-1 text-sm bg-[#282928] text-stone-200 px-2 py-1 rounded-md border border-[#383938]">
                    <Tag size={10} className="text-[#D1E8C5]" />
                    <span>{value}</span>
                  </div>
                );
              })}
              {Object.values(sessionState).every(v => !v || v === '未知') && (
                <p className="text-xs text-stone-600 italic">暂无偏好标签</p>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-[#282928]">
            <div className="flex items-center justify-between px-2 mb-2">
              <p className="text-sm font-semibold text-stone-500 uppercase tracking-wider">
                我的歌单
              </p>
              <button 
                onClick={() => setIsModalOpen(true)}
                className="p-1 hover:bg-[#282928] rounded-md transition-colors text-stone-400 hover:text-white"
                title="新建歌单"
              >
                <Plus size={16} />
              </button>
            </div>
            {playlists.map((playlist) => (
              <NavItem 
                key={playlist.id} 
                icon={<ListMusic size={20} />} 
                label={playlist.name} 
                active={location.pathname === `/playlists/${playlist.id}`}
                onClick={() => navigate(`/playlists/${playlist.id}`)}
              />
            ))}
          </div>
        </nav>

        <div className="p-4 border-t border-[#282928]">
            <div className="flex items-center gap-3 p-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-[#282928] flex items-center justify-center text-xs font-bold text-[#D1E8C5] border border-[#383938]">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.username || '未登录'}</p>
              <p className="text-xs text-stone-500 truncate">@{user?.username || 'guest'}</p>
            </div>
          </div>
          <button 
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-stone-400 hover:text-white hover:bg-[#282928] rounded-lg transition-all"
          >
            <LogOut size={18} />
            <span>退出登录</span>
          </button>
        </div>
      </aside>

      {/* Create Playlist Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-bold text-[#1A1A1A] mb-4">创建新歌单</h3>
            <form onSubmit={handleCreatePlaylist}>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1">歌单名称</label>
                  <input 
                    autoFocus 
                    value={newPlaylistName} 
                    onChange={e => setNewPlaylistName(e.target.value)} 
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:border-[#1C1D1C] focus:ring-1 focus:ring-[#1C1D1C] outline-none text-[#1A1A1A]" 
                    placeholder="例如：深夜工作专属" 
                    required 
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1">歌单描述 (可选)</label>
                  <textarea 
                    value={newPlaylistDesc} 
                    onChange={e => setNewPlaylistDesc(e.target.value)} 
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:border-[#1C1D1C] focus:ring-1 focus:ring-[#1C1D1C] outline-none resize-none h-20 text-[#1A1A1A]" 
                    placeholder="描述一下这个歌单的氛围..." 
                  />
                </div>
              </div>
              {error && (
                <div className="mt-4 p-2 bg-rose-50 border border-rose-100 rounded-lg text-rose-600 text-xs">
                  {error}
                </div>
              )}
              <div className="flex justify-end gap-2 mt-6">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)} 
                  className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                  disabled={isCreating}
                >
                  取消
                </button>
                <button 
                  type="submit" 
                  disabled={isCreating}
                  className="px-4 py-2 text-sm font-medium bg-[#1C1D1C] text-[#D1E8C5] rounded-lg hover:bg-[#282928] disabled:opacity-50"
                >
                  {isCreating ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* User Profile Modal */}
      {isProfileModalOpen && (
        <UserProfileModal onClose={() => setIsProfileModalOpen(false)} />
      )}
    </>
  );
}

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, active = false, onClick }) => {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all",
        active 
          ? "bg-[#282928] text-[#D1E8C5]" 
          : "text-stone-400 hover:text-stone-200 hover:bg-[#282928]/50"
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  );
};
