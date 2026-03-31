import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { RecommendationPanel } from './components/RecommendationPanel';
import { Message, SessionContext, Track } from './types';
import { INITIAL_MESSAGES } from './mock/mock_data';
import { getMockResponse } from './mock/mock_logic';
import { fetchHealth, HealthStatus } from './services/health';
import { sendChatMessage } from './services/chat';
import { resetSession, fetchSession } from './services/session';
import { sendFeedback } from './services/feedback';
import { mapSessionSummaryToSessionContext } from './mappers/session_summary_to_context';
import { mapChatStateToSessionContext } from './mappers/state_to_context';
import { mapRecommendationsToTracks } from './mappers/recommendations_to_tracks';
import { AudioPlayerProvider } from './contexts/AudioPlayerContext';

export default function App() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [context, setContext] = useState<SessionContext>({
    mood: [],
    scene: [],
    genre: [],
    energy: [],
    vocal: []
  });
  const [tracks, setTracks] = useState<Track[]>([]);
  const [systemStatus, setSystemStatus] = useState<HealthStatus | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [loadingStage, setLoadingStage] = useState<number>(0);

  const LOADING_STAGES = [
    '正在分析用户场景...',
    '正在分析用户情绪...',
    '正在分析音乐流派偏好...',
    '正在分析能量偏好...',
    '正在为你精选歌曲...',
  ];

  useEffect(() => {
    const getHealth = async () => {
      const status = await fetchHealth();
      setSystemStatus(status);
    };
    getHealth();
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const recoverSession = async () => {
      try {
        const response = await fetchSession(sessionId);
        if (response.ok && response.state) {
          setContext(mapSessionSummaryToSessionContext(response.state));
        }
      } catch (error) {
        console.error('Failed to recover session:', error);
      }
    };

    recoverSession();
  }, [sessionId]);

  const handleSendMessage = async (content: string) => {
    const newUserMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, newUserMsg]);

    if (isSending) {
      return;
    }

    const loadingMessageId = `loading-${Date.now()}`;
    const loadingMsg: Message = {
      id: loadingMessageId,
      role: 'agent',
      content: LOADING_STAGES[0],
      timestamp: new Date()
    };

    setMessages(prev => [...prev, loadingMsg]);
    setIsSending(true);
    setLoadingStage(0);

    const stageInterval = setInterval(() => {
      setLoadingStage((prev) => {
        if (prev >= LOADING_STAGES.length - 1) {
          return prev;
        }
        const next = prev + 1;
        setMessages(prevMsgs => 
          prevMsgs.map(msg => 
            msg.id === loadingMessageId 
              ? { ...msg, content: LOADING_STAGES[next] }
              : msg
          )
        );
        return next;
      });
    }, 3000);

    try {
      const response = await sendChatMessage({
        session_id: sessionId ?? undefined,
        message: content,
      });

      setSessionId(response.session_id);
      setContext(mapChatStateToSessionContext(response.state));
      setTracks(mapRecommendationsToTracks(response.recommendations));

      const newAgentMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: response.assistant_text,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, newAgentMsg]);
    } catch (error) {
      const fallbackMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: '抱歉，连接后端服务失败，已自动切换到演示模式为你继续推荐。',
        timestamp: new Date()
      };

      const { context: nextContext, tracks: nextTracks } = getMockResponse(content);
      setContext(nextContext);
      setTracks(nextTracks);
      setMessages(prev => [...prev, fallbackMsg]);
    } finally {
      clearInterval(stageInterval);
      setMessages(prev => prev.filter(message => message.id !== loadingMessageId));
      setIsSending(false);
    }
  };

  const handleResetSession = async () => {
    if (!sessionId) return;

    try {
      const result = await resetSession(sessionId);
      if (result.ok) {
        setMessages(INITIAL_MESSAGES);
        setTracks([]);
        setContext({
          mood: [],
          scene: [],
          genre: [],
          energy: [],
          vocal: []
        });
        setIsSending(false);
      } else {
        throw new Error('Reset failed');
      }
    } catch (error) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'agent',
        content: '抱歉，重置会话失败。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    }
  };

  const handleFeedback = async (message: string) => {
    if (!sessionId) {
      console.error('No session ID for feedback');
      return false;
    }

    const isRefresh = message === '换一批';
    const isDislike = message.includes('不喜欢');
    const isLike = message.includes('喜欢');

    const feedbackType = isRefresh ? 'refresh' : isDislike ? 'dislike' : isLike ? 'like' : 'refresh';
    
    const trackIdMatch = message.match(/id\s*[:：]\s*(\S+)/);
    const trackId = trackIdMatch ? trackIdMatch[1] : '';

    try {
      const response = await sendFeedback({
        session_id: sessionId,
        feedback_type: feedbackType as 'like' | 'dislike' | 'refresh',
        track_id: trackId,
        track_metadata: {},
        recommendation_context: {},
      });

      if (response.success && response.ack_message) {
        const ackMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'agent',
          content: response.ack_message,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, ackMsg]);
      }

      if (isRefresh) {
        const chatResponse = await sendChatMessage({
          session_id: sessionId,
          message: '换一批',
        });
        setTracks(mapRecommendationsToTracks(chatResponse.recommendations));
      } else if (isDislike && trackId) {
        setTracks(prev => prev.filter(t => t.id !== trackId));
      }

      return true;
    } catch (error) {
      console.error('Feedback failed:', error);
      
      try {
        const response = await sendChatMessage({
          session_id: sessionId,
          message: message,
        });
        
        if (isRefresh) {
          setTracks(mapRecommendationsToTracks(response.recommendations));
        } else if (isDislike && trackId) {
          setTracks(prev => prev.filter(t => t.id !== trackId));
        }
        
        return true;
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        return false;
      }
    }
  };

  return (
    <AudioPlayerProvider>
      <div className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans text-slate-900">
        <Sidebar 
          context={context} 
          systemStatus={systemStatus} 
          sessionId={sessionId} 
          onResetSession={handleResetSession}
        />
        <main className="flex-1 flex min-w-0">
          <ChatArea messages={messages} onSendMessage={handleSendMessage} />
          <RecommendationPanel tracks={tracks} onFeedback={handleFeedback} />
        </main>
      </div>
    </AudioPlayerProvider>
  );
}
