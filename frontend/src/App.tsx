import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';
import Sidebar from './components/layout/Sidebar';
import ChatArea from './components/layout/ChatArea';
import RecommendationPanel from './components/layout/RecommendationPanel';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import HistoryPage from './components/pages/HistoryPage';
import PlaylistPage from './components/pages/PlaylistPage';
import LandingPage from './components/pages/LandingPage';
import { Loader2 } from 'lucide-react';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F4F5F0] flex items-center justify-center">
        <Loader2 className="animate-spin text-[#1C1D1C]" size={40} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/welcome" />;
  }

  return <>{children}</>;
}

function MainLayout() {
  return (
    <div className="flex h-screen bg-[#F4F5F0] text-[#1A1A1A] overflow-hidden font-sans selection:bg-[#D1E8C5]/50">
      <Sidebar />
      <Outlet />
    </div>
  );
}

function DiscoverPage() {
  return (
    <>
      <ChatArea />
      <RecommendationPanel />
    </>
  );
}

function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/" />;
  }

  return isLogin ? (
    <Login onToggle={() => setIsLogin(false)} />
  ) : (
    <Register onToggle={() => setIsLogin(true)} />
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          } 
        >
          <Route index element={<DiscoverPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="playlists/:id" element={<PlaylistPage />} />
        </Route>
        <Route path="/welcome" element={<LandingPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}
