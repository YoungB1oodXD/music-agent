import React, { useState } from 'react';
import { Lock, ArrowRight, Github, Loader2, Music, User } from 'lucide-react';
import { motion } from 'motion/react';
import { useAuthStore } from '../../store/useAuthStore';

export default function Login({ onToggle }: { onToggle: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ username, password });
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
          <h1 className="text-3xl font-bold text-[#1A1A1A] tracking-tight">欢迎回来</h1>
          <p className="text-gray-500 mt-2 text-sm">登录 Mustify，继续你的音乐旅程</p>
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
                placeholder="your_username"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between ml-1">
              <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">访问密码</label>
              <button type="button" className="text-xs text-[#1C1D1C] hover:underline font-medium">忘记密码？</button>
            </div>
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
                placeholder="••••••••"
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
                <span>立即登录</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 flex items-center gap-4">
          <div className="h-[1px] flex-1 bg-gray-200" />
          <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">或者使用</span>
          <div className="h-[1px] flex-1 bg-gray-200" />
        </div>

        <div className="mt-6">
          <button className="w-full bg-white hover:bg-gray-50 text-[#1A1A1A] font-medium py-3 rounded-xl border border-gray-200 shadow-sm transition-all flex items-center justify-center gap-3">
            <Github size={20} />
            <span>GitHub 账号登录</span>
          </button>
        </div>

        <p className="mt-8 text-center text-sm text-gray-500">
          还没有账号？ <button onClick={onToggle} className="text-[#1C1D1C] hover:underline font-bold">立即注册</button>
        </p>
      </motion.div>
    </div>
  );
}
