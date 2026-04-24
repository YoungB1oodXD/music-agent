import React from 'react';
import { Link } from 'react-router-dom';
import { Music, Sparkles, Brain, Radio, ArrowRight, Github } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';

export default function LandingPage() {
    const { isAuthenticated } = useAuthStore();
    const ctaLink = isAuthenticated ? "/" : "/login";
    const ctaText = isAuthenticated ? "进入控制台" : "开始使用";
    const ctaHeroText = isAuthenticated ? "返回你的音乐宇宙" : "进入你的音乐宇宙";

    return (
        <div className="min-h-screen bg-[#F4F5F0] text-[#1C1D1C] font-sans selection:bg-[#D1E8C5]/50 overflow-x-hidden">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 py-6 px-8 flex items-center justify-between z-50 mix-blend-difference text-white">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-[#D1E8C5] rounded-xl flex items-center justify-center shadow-lg">
                        <Music className="text-[#1C1D1C] w-6 h-6" />
                    </div>
                    <span className="text-2xl font-black tracking-tight text-white drop-shadow-sm">Mustify<span className="text-[#D1E8C5]">.</span></span>
                </div>
                <div className="flex items-center gap-6 text-sm font-medium">
                    <a href="#features" className="hover:text-[#D1E8C5] transition-colors">特性</a>
                    <a href="#how-it-works" className="hover:text-[#D1E8C5] transition-colors">如何工作</a>
                    <Link to={ctaLink} className="px-5 py-2.5 bg-white text-[#1C1D1C] rounded-full hover:bg-[#D1E8C5] transition-all transform hover:scale-105 active:scale-95 shadow-lg">
                        {ctaText}
                    </Link>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative min-h-[90vh] flex items-center justify-center pt-20 px-4">
                {/* Abstract Background Shapes */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[#D1E8C5]/40 rounded-full blur-3xl opacity-50 -z-10 animate-pulse"></div>
                <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-stone-300/30 rounded-full blur-3xl opacity-50 -z-10"></div>

                <div className="max-w-5xl mx-auto text-center z-10 flex flex-col items-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/60 border border-stone-200/50 backdrop-blur-md text-xs font-semibold uppercase tracking-widest text-stone-600 mb-8 shadow-sm">
                        <Sparkles size={14} className="text-[#1C1D1C]" />
                        <span>智能音乐编排引擎</span>
                    </div>
                    <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-[#1C1D1C] leading-[1.1] mb-8">
                        通过对话，<br className="hidden md:block" />
                        发现<span className="relative inline-block px-4"><span className="relative z-10">灵魂共鸣</span><span className="absolute bottom-2 left-0 w-full h-8 bg-[#D1E8C5] -z-10 -rotate-2 scale-110"></span></span>的旋律。
                    </h1>
                    <p className="text-xl md:text-2xl text-stone-600 max-w-2xl mb-12 leading-relaxed font-medium">
                        Mustify 利用先进的大语言模型，根据您的情绪、场景和喜好，为您精准生成个性化歌单，并提供深度的 AI 推荐理由。
                    </p>
                    <div className="flex flex-col sm:flex-row items-center gap-4">
                        <Link to={ctaLink} className="h-14 px-8 bg-[#1C1D1C] text-[#D1E8C5] rounded-full flex items-center justify-center gap-2 text-lg font-bold hover:bg-[#282928] transition-all transform hover:scale-105 active:scale-95 shadow-xl hover:shadow-2xl">
                            {ctaHeroText} <ArrowRight size={20} />
                        </Link>
                        <a href="#features" className="h-14 px-8 bg-white border border-stone-200 text-[#1C1D1C] rounded-full flex items-center justify-center text-lg font-bold hover:bg-stone-50 transition-all">
                            了解更多
                        </a>
                    </div>
                </div>
            </section>

            {/* Features Bento Grid */}
            <section id="features" className="py-32 px-4 md:px-8 max-w-7xl mx-auto">
                <div className="text-center mb-20">
                    <h2 className="text-4xl md:text-5xl font-black tracking-tight mb-4">不仅仅是推荐系统</h2>
                    <p className="text-stone-500 text-lg">Mustify 重新定义了您与音乐的连接方式。</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[320px]">
                    {/* Card 1 */}
                    <div className="md:col-span-2 bg-[#1C1D1C] rounded-[2rem] p-10 flex flex-col justify-between text-white relative overflow-hidden group shadow-2xl">
                        <div className="absolute top-0 right-0 p-8 opacity-20 transform group-hover:scale-110 group-hover:rotate-12 transition-all duration-700">
                            <Brain size={160} />
                        </div>
                        <div className="relative z-10">
                            <div className="w-12 h-12 bg-[#282928] rounded-2xl flex items-center justify-center mb-6 border border-[#383938]">
                                <Sparkles className="text-[#D1E8C5]" size={24} />
                            </div>
                            <h3 className="text-3xl font-bold mb-4">自然语言对话点歌</h3>
                            <p className="text-stone-400 text-lg max-w-md leading-relaxed">
                                无需思考复杂的关键词，像和朋友聊天一样描述你的感受：“我需要一些适合深夜加班，能让人保持专注但又不吵闹的电子乐”。AI 将瞬间理解并给出完美回应。
                            </p>
                        </div>
                    </div>

                    {/* Card 2 */}
                    <div className="bg-[#D1E8C5] rounded-[2rem] p-10 flex flex-col justify-between text-[#1C1D1C] relative overflow-hidden group shadow-xl">
                        <div className="relative z-10">
                            <div className="w-12 h-12 bg-white/50 backdrop-blur-sm rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                                <Radio className="text-[#1C1D1C]" size={24} />
                            </div>
                            <h3 className="text-2xl font-bold mb-3">深度推荐理由</h3>
                            <p className="text-stone-700 text-base leading-relaxed">
                                不再是对着封面盲盒。每一首推荐的歌曲都配有专属的 AI 分析，告诉你这首歌的合成器音效、贝斯线为何能触动你当前的情绪。
                            </p>
                        </div>
                    </div>

                    {/* Card 3 */}
                    <div className="bg-white rounded-[2rem] p-10 flex flex-col justify-between text-[#1C1D1C] relative overflow-hidden group shadow-xl border border-stone-200/50">
                        <div className="relative z-10">
                            <h3 className="text-2xl font-bold mb-2">情境偏好捕捉</h3>
                            <p className="text-stone-500 text-sm leading-relaxed mb-6">
                                自动提取交流中的心情、场景与风格标签，生成你的专属音乐指纹。
                            </p>
                            <div className="flex flex-wrap gap-2">
                                <span className="px-3 py-1.5 bg-stone-100 rounded-lg text-xs font-bold text-stone-600">深夜工作</span>
                                <span className="px-3 py-1.5 bg-stone-100 rounded-lg text-xs font-bold text-stone-600">专注</span>
                                <span className="px-3 py-1.5 bg-stone-100 rounded-lg text-xs font-bold text-stone-600">合成器波</span>
                            </div>
                        </div>
                    </div>

                    {/* Card 4 */}
                    <div className="md:col-span-2 bg-[#F4F5F0] rounded-[2rem] p-1 flex justify-end items-end relative overflow-hidden group border border-stone-200">
                        <div className="absolute inset-0 bg-[url('https://picsum.photos/seed/playlist/1000/600')] bg-cover bg-center opacity-40 group-hover:opacity-50 transition-opacity mix-blend-luminosity"></div>
                        <div className="absolute inset-0 bg-gradient-to-t from-[#1C1D1C] via-[#1C1D1C]/60 to-transparent"></div>
                        <div className="relative z-10 p-10 text-white w-full">
                            <h3 className="text-3xl font-bold mb-3 drop-shadow-md">一键生成定制歌单</h3>
                            <p className="text-stone-300 text-lg max-w-lg mb-6 drop-shadow-md">
                                将喜欢的推荐曲目轻松归档，支持无缝添加与删减，打造您的专属数字唱片架，管理音乐从未如此优雅。
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Minimal Footer */}
            <footer className="py-12 border-t border-stone-200/60 bg-white text-center flex flex-col items-center">
                <div className="w-12 h-12 bg-[#1C1D1C] rounded-2xl flex items-center justify-center mb-6">
                    <Music className="text-[#D1E8C5]" size={24} />
                </div>
                <h4 className="text-xl font-black mb-2">Mustify.</h4>
                <p className="text-stone-500 text-sm mb-6">下一代 AI 音乐探索平台</p>
                <div className="flex items-center gap-4">
                    <a href="#" className="p-2 text-stone-400 hover:text-[#1C1D1C] hover:bg-stone-100 rounded-full transition-colors"><Github size={20} /></a>
                </div>
                <p className="text-xs text-stone-400 mt-8 font-mono">© 2026 Mustify Inc. All rights reserved.</p>
            </footer>
        </div>
    );
}
