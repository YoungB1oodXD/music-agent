import React from 'react';
import { motion } from 'motion/react';
import { Activity, Disc3, Hash, Sparkles, Zap, Mic2, Server, Database, Cpu, Network } from 'lucide-react';
import { SessionContext } from '../types';

interface SidebarProps {
  context: SessionContext;
  sessionId?: string | null;
  systemStatus?: {
    status?: string;
    llm_mode?: string;
  } | null;
  onResetSession?: () => void;
}

export function Sidebar({ context, sessionId, systemStatus, onResetSession }: SidebarProps) {
  const demoStatus = [
    { label: 'RAG', icon: <Network className="w-3.5 h-3.5 text-slate-400"/>, value: 'Active', color: 'text-emerald-600' },
    { label: 'Vector DB', icon: <Database className="w-3.5 h-3.5 text-slate-400"/>, value: 'Connected', color: 'text-emerald-600' },
    { label: 'Hybrid Recommender', icon: <Sparkles className="w-3.5 h-3.5 text-slate-400"/>, value: 'Online', color: 'text-emerald-600' },
  ];

  return (
    <aside className="w-72 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col h-full overflow-y-auto p-5 shadow-sm z-10">
      <div className="flex flex-col gap-1 mb-8 px-1 mt-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-indigo-500 flex items-center justify-center shadow-md shadow-indigo-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <h1 className="font-display font-bold text-xl tracking-tight text-slate-900">音乐推荐 Agent</h1>
        </div>
        <p className="text-xs text-slate-500 font-medium ml-11">Conversational Music Recommender</p>
      </div>

      <div className="space-y-6 flex-1">
        <ContextSection title="当前情绪" icon={<Activity className="w-4 h-4" />} items={context.mood} color="text-indigo-600" bg="bg-indigo-50" border="border-indigo-100" />
        <ContextSection title="当前场景" icon={<Disc3 className="w-4 h-4" />} items={context.scene} color="text-emerald-600" bg="bg-emerald-50" border="border-emerald-100" />
        <ContextSection title="音乐风格" icon={<Hash className="w-4 h-4" />} items={context.genre} color="text-purple-600" bg="bg-purple-50" border="border-purple-100" />
        <ContextSection title="能量偏好" icon={<Zap className="w-4 h-4" />} items={context.energy} color="text-amber-600" bg="bg-amber-50" border="border-amber-100" />
        <ContextSection title="人声偏好" icon={<Mic2 className="w-4 h-4" />} items={context.vocal} color="text-rose-600" bg="bg-rose-50" border="border-rose-100" />
      </div>

      <div className="mt-8 p-4 rounded-2xl bg-slate-50 border border-gray-200 shadow-sm">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Server className="w-4 h-4" />
          系统状态 (System Status)
        </h3>
        <ul className="space-y-2.5 text-xs text-slate-600">
          <li className="flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Hash className="w-3.5 h-3.5 text-slate-400"/> Session:</span>
            <div className="flex flex-col items-end gap-1">
              <span className="font-semibold text-slate-800 truncate max-w-[120px]" title={sessionId || 'Not set'}>
                {sessionId || 'Not set'}
              </span>
              {sessionId && onResetSession && (
                <button 
                  onClick={onResetSession}
                  className="text-[10px] text-indigo-600 hover:text-indigo-700 font-medium underline underline-offset-2 transition-colors"
                >
                  重置会话
                </button>
              )}
            </div>
          </li>
          <li className="flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-slate-400"/> LLM:</span>
            <span className="font-semibold text-slate-800 capitalize">{systemStatus?.llm_mode || 'Qwen'}</span>
          </li>
          <li className="flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-slate-400"/> Backend:</span>
            <span className={`font-semibold ${systemStatus?.status === 'ok' ? 'text-emerald-600' : 'text-rose-600'}`}>
              {systemStatus?.status || 'Unknown'}
            </span>
          </li>
          {demoStatus.map((item) => (
            <li key={item.label} className="flex items-center justify-between">
              <span className="flex items-center gap-1.5">{item.icon} {item.label}:</span>
              <span className={`font-semibold ${item.color}`}>{item.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function ContextSection({ title, icon, items, color, bg, border }: { title: string, icon: React.ReactNode, items: string[], color: string, bg: string, border: string }) {
  return (
    <div className="px-1">
      <h3 className="text-xs font-semibold text-slate-500 mb-2.5 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <div className="flex flex-wrap gap-2">
        {items.length > 0 ? items.map((item, i) => (
          <motion.span
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            key={item}
            className={`text-xs px-2.5 py-1 rounded-lg border font-medium shadow-sm ${color} ${bg} ${border}`}
          >
            {item}
          </motion.span>
        )) : (
          <span className="text-xs text-slate-400 italic">分析中...</span>
        )}
      </div>
    </div>
  );
}
