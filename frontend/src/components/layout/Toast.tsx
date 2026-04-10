import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, XCircle, Heart, RefreshCw, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, duration?: number) => void;
  showLike: (songTitle?: string) => void;
  showDislike: (songTitle?: string) => void;
  showAddToPlaylist: (playlistName: string, songTitle: string) => void;
  showRefresh: () => void;
  showError: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts(prev => [...prev, { id, type, message }]);
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
  }, [removeToast]);

  const showLike = useCallback((songTitle?: string) => {
    showToast('success', songTitle ? `已收到你对《${songTitle}》的喜欢` : '已收到你的喜欢');
  }, [showToast]);

  const showDislike = useCallback((songTitle?: string) => {
    showToast('success', songTitle ? `已收到你对《${songTitle}》的反馈，后续会避开类似歌曲` : '已收到反馈，后续会避开类似歌曲');
  }, [showToast]);

  const showAddToPlaylist = useCallback((playlistName: string, songTitle: string) => {
    showToast('success', `《${songTitle}》已添加到「${playlistName}」`);
  }, [showToast]);

  const showRefresh = useCallback(() => {
    showToast('info', '正在为你换一批推荐...');
  }, [showToast]);

  const showError = useCallback((message: string) => {
    showToast('error', message);
  }, [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, showLike, showDislike, showAddToPlaylist, showRefresh, showError }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
        <RenderToasts toasts={toasts} onRemove={removeToast} />
      </div>
    </ToastContext.Provider>
  );
}

function RenderToasts({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  const items = toasts.map((t) => (
    <ToastItem key={t.id} toast={t} onClose={() => onRemove(t.id)} />
  ));
  return <>{items}</>;
}

const ToastItem: React.FC<{ toast: Toast; onClose: () => void }> = ({ toast, onClose }) => {
  const bgColor = {
    success: 'bg-emerald-600',
    error: 'bg-rose-600',
    info: 'bg-slate-700',
  }[toast.type];

  const Icon = {
    success: Heart,
    error: XCircle,
    info: RefreshCw,
  }[toast.type];

  return (
    <div 
      className={`${bgColor} text-white px-5 py-3 rounded-xl shadow-xl flex items-center gap-3 pointer-events-auto`}
    >
      <Icon size={18} className="shrink-0" />
      <p className="text-sm font-medium flex-1">{toast.message}</p>
      <button onClick={onClose} className="shrink-0 hover:opacity-70 transition-opacity">
        <X size={16} />
      </button>
    </div>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
