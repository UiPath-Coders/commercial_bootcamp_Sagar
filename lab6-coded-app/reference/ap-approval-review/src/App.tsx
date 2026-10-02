import { useState } from 'react';
import { useAuth } from '@/auth/AuthProvider';
import { isEntityIdConfigured } from '@/config/uipath';
import { GatePage } from '@/screens/GatePage';
import { Worklist } from '@/screens/Worklist';
import { ConfigMissingPage, LoadingPage, SignInPage } from '@/components/StateViews';

/**
 * Screen flow:
 *   not signed in      -> SignInPage (starts PKCE)          [auth-error state lives here]
 *   signed in          -> GatePage (Screen 1)               [never before / during login]
 *   "Yes, I am winner" -> Worklist (Screen 2)
 * No client-side router is needed for two screens, which also sidesteps the
 * deployed-app base-path pitfall (see README).
 */
export function App() {
  const { isAuthenticated, isLoading, error, login } = useAuth();
  const [passedGate, setPassedGate] = useState(false);

  if (isLoading) return <LoadingPage label="Signing you in" />;
  if (!isAuthenticated) return <SignInPage onLogin={login} error={error} />;
  if (!isEntityIdConfigured()) return <ConfigMissingPage />;
  if (!passedGate) return <GatePage onContinue={() => setPassedGate(true)} />;
  return <Worklist />;
}
