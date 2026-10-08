import { useState } from 'react';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { SignInPage } from './screens/SignInPage';
import { GatePage } from './screens/GatePage';
import { Worklist } from './screens/Worklist';

type Screen = 'gate' | 'worklist';

function AppContent() {
  const { isAuthenticated, isLoading, error, login } = useAuth();
  const [screen, setScreen] = useState<Screen>('gate');

  // The gate is never rendered before or during login.
  if (!isAuthenticated) {
    return <SignInPage onSignIn={login} isLoading={isLoading} error={error} />;
  }

  if (screen === 'gate') return <GatePage onContinue={() => setScreen('worklist')} />;
  return <Worklist />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
