import { useEffect, MouseEvent, useState } from 'react';
import { History, MessageSquare, ChevronRight, Plus, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useChatStore } from '../../store/useChatStore';

export default function HistoryPage() {
  const { sessions, loadSession, fetchSessions, deleteSession, createNewSession } = useChatStore();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    fetchSessions()
      .catch((err: Error) => setError(err.message || '加载失败'))
      .finally(() => setIsLoading(false));
  }, []);

  const handleLoadSession = (id: string) => {
    loadSession(id);
    navigate('/');
  };

  const handleDeleteSession = (e: MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('确定删除该会话？')) {
      deleteSession(id);
    }
  };

  const handleNewSession = () => {
    createNewSession();
    navigate('/');
  };

  return (
    <main className="flex-1 flex flex-col bg-[#F4F5F0] relative overflow-hidden">
      <header className="h-16 border-b border-gray-200 flex items-center justify-between px-8 bg-[#F4F5F0]/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <History className="text-[#1C1D1C] w-5 h-5" />
          <h2 className="font-semibold text-[#1A1A1A]">最近对话</h2>
        </div>
        <button
          onClick={handleNewSession}
          className="flex items-center gap-2 bg-[#1C1D1C] text-[#D1E8C5] px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#282928] transition-colors shadow-sm"
        >
          <Plus size={16} />
          <span>新对话</span>
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto space-y-4">
          {isLoading ? (
            <div className="text-center py-20 text-gray-500">
              <div className="animate-spin w-8 h-8 border-2 border-gray-300 border-t-[#1C1D1C] rounded-full mx-auto mb-4" />
              <p>加载中...</p>
            </div>
          ) : error ? (
            <div className="text-center py-20 text-red-500">
              <p>{error}</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-20 text-gray-500">
              <MessageSquare size={48} className="mx-auto mb-4 opacity-20" />
              <p>暂无对话记录</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleLoadSession(session.id)}
                className="bg-white border border-gray-200 rounded-2xl p-5 hover:border-gray-300 hover:shadow-md transition-all cursor-pointer group"
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-bold text-[#1A1A1A] group-hover:text-[#1C1D1C] transition-colors">
                    {session.title || '新对话'}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 font-mono">
                      {new Date(session.createdAt).toLocaleDateString()}{' '}
                      {new Date(session.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button
                      onClick={(e) => handleDeleteSession(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded-md transition-all"
                      title="删除会话"
                    >
                      <Trash2 size={14} className="text-red-400 hover:text-red-600" />
                    </button>
                  </div>
                </div>

                <p className="text-sm text-gray-500 line-clamp-2 mb-4">
                  {session.title || '没有用户消息'}
                </p>

                <div className="flex items-center justify-end">
                  <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center text-gray-400 group-hover:bg-[#1C1D1C] group-hover:text-[#D1E8C5] transition-colors">
                    <ChevronRight size={16} />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  );
}
