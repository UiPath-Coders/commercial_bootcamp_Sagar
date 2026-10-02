import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/globals.css';
import { App } from './App';
import { AuthProvider } from './auth/AuthProvider';

const container = document.getElementById('root');
if (!container) throw new Error('No #root element found');

createRoot(container).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
