import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import {AudioPlayerProvider} from './contexts/AudioPlayerContext';
import {ToastProvider} from './components/layout/Toast';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AudioPlayerProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </AudioPlayerProvider>
  </StrictMode>,
);
