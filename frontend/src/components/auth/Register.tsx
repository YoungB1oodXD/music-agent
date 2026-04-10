import React, { useState } from 'react';
import { Lock, ArrowRight, Github, Loader2, Music, User } from 'lucide-react';
import { motion } from 'motion/react';
import { useAuthStore } from '../../store/useAuthStore';

export default function Register({ onToggle }: { onToggle: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { register, isLoading, error } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await register({ username, password });
  };

  return (
    <div className="min-h-screen bg-[#F4F5F0] flex items-center justify-center p-6 relative overflow-hidden">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-white border border-gray-200 rounded-3xl p-8 shadow-xl relative z-10"
      >
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-16 h-16 bg-[#D1E8C5] rounded-2xl flex items-center justify-center shadow-sm mb-4">
            <Music className="text-[#1C1D1C] w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold text-[#1A1A1A] tracking-tight">创建账号</h1>
          <p className="text-gray-500 mt-2 text-sm">加入 Mustify，开启智能音乐体验</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">用户名</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-[#1C1D1C] transition-colors">
                <User size={18} />
              </div>
              <input 
                type="text" 
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 focus:border-[#1C1D1C] focus:ring-4 focus:ring-[#1C1D1C]/5 rounded-xl py-3 pl-12 pr-4 text-[#1A1A1A] placeholder:text-gray-400 transition-all outline-none"
                placeholder="你的昵称"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">设置密码</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-[#1C1D1C] transition-colors">
                <Lock size={18} />
              </div>
              <input 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 focus:border-[#1C1D1C] focus:ring-4 focus:ring-[#1C1D1C]/5 rounded-xl py-3 pl-12 pr-4 text-[#1A1A1A] placeholder:text-gray-400 transition-all outline-none"
                placeholder="至少 8 位字符"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-600 text-xs font-medium">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-[#1C1D1C] hover:bg-[#282928] disabled:bg-gray-200 disabled:text-gray-400 text-[#D1E8C5] font-bold py-3 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 group"
          >
            {isLoading ? <Loader2 className="animate-spin" size={20} /> : (
              <>
                <span>注册账号</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-gray-500">
          已有账号？ <button onClick={onToggle} className="text-[#1C1D1C] hover:underline font-bold">直接登录</button>
        </p>
      </motion.div>
    </div>
  );
}
