import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Bot, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useChatStore } from '../../store/useChatStore';
import { cn } from '../../lib/utils';

const THINKING_STEPS = [
  "正在思考你的需求",
  "正在分析音乐偏好",
  "正在理解场景风格",
  "正在搜索适合的歌曲",
  "正在生成推荐理由",
];

export default function ChatArea() {
  const { messages, sendMessage, isLoading } = useChatStore();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const [thinkingStep, setThinkingStep] = useState(0);

  useEffect(() => {
    if (isLoading) {
      setThinkingStep(0);
      const interval = setInterval(() => {
        setThinkingStep((prev) => (prev + 1) % THINKING_STEPS.length);
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const content = input;
    setInput('');
    await sendMessage(content);
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <main className="flex-1 flex flex-col bg-[#F4F5F0] relative overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-gray-200 flex items-center justify-between px-8 bg-[#F4F5F0]/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="text-[#1C1D1C] w-5 h-5" />
            <h2 className="font-semibold text-[#1A1A1A]">Mustify AI</h2>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "flex gap-4 max-w-3xl mx-auto",
                msg.role === 'user' ? "flex-row-reverse" : "flex-row"
              )}
            >
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border",
                msg.role === 'user' 
                  ? "bg-[#1C1D1C] border-[#282928] text-[#D1E8C5]" 
                  : "bg-white border-gray-200 text-[#1C1D1C] shadow-sm"
              )}>
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className={cn(
                "flex flex-col gap-2",
                msg.role === 'user' ? "items-end" : "items-start"
              )}>
                <div className={cn(
                  "px-5 py-4 rounded-2xl text-xs leading-relaxed shadow-sm",
                  msg.role === 'user' 
                    ? "bg-[#1C1D1C] text-[#D1E8C5] rounded-tr-none" 
                    : "bg-white text-[#1A1A1A] border border-gray-100 rounded-tl-none"
                )}>
                  {msg.content}
                </div>
                <span className="text-[10px] text-gray-400 font-mono">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </motion.div>
          ))}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-4 max-w-3xl mx-auto"
            >
              <div className="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center text-[#1C1D1C] shrink-0 shadow-sm">
                <Loader2 className="animate-spin" size={20} />
              </div>
              <div className="bg-white border border-gray-100 px-4 py-3 rounded-2xl rounded-tl-none flex items-center gap-2 shadow-sm">
                <span className="text-xs text-gray-600">{THINKING_STEPS[thinkingStep]}</span>
                <span className="w-1.5 h-1.5 bg-[#1C1D1C] rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-[#1C1D1C] rounded-full animate-bounce [animation-delay:0.2s]" />
                <span className="w-1.5 h-1.5 bg-[#1C1D1C] rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Input Suggestions */}
        <div className="max-w-3xl mx-auto mb-3">
          <div className="flex flex-wrap gap-2 justify-center">
            {[
              { text: '推荐适合专注工作的音乐', emoji: '🎯' },
              { text: '来点轻松愉快的歌', emoji: '😊' },
              { text: '深夜独处时听的', emoji: '🌙' },
              { text: '健身运动时听的', emoji: '💪' },
            ].map((item) => (
              <button
                key={item.text}
                onClick={() => sendMessage(item.text)}
                className="group px-4 py-2 bg-white border border-gray-200 text-sm rounded-full hover:bg-[#1C1D1C] hover:text-[#D1E8C5] hover:border-[#1C1D1C] transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>{item.emoji}</span>
                <span className="font-medium">{item.text}</span>
              </button>
            ))}
          </div>
        </div>

      {/* Input Area */}
      <div className="p-8 pt-0 bg-gradient-to-t from-[#F4F5F0] via-[#F4F5F0] to-transparent">
        <div className="max-w-3xl mx-auto relative group">
          <div className="relative flex items-center bg-white border border-gray-200 rounded-2xl p-2 shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="描述你现在的心情或想听的场景..."
              className="flex-1 bg-transparent border-none focus:ring-0 text-[#1A1A1A] px-4 py-3 placeholder:text-gray-400 text-sm outline-none"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center transition-all",
                input.trim() && !isLoading 
                  ? "bg-[#1C1D1C] text-[#D1E8C5] shadow-md hover:scale-105" 
                  : "bg-gray-100 text-gray-400"
              )}
            >
              <Send size={18} />
            </button>
          </div>
          <p className="mt-3 text-center text-[10px] text-gray-400 uppercase tracking-widest">
            Mustify AI · 音乐旅程编排助手
          </p>
        </div>
      </div>
    </main>
  );
}
