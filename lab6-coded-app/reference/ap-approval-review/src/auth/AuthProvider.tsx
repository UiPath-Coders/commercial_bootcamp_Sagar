import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { UiPath, UiPathError } from '@uipath/uipath-typescript/core';
import { ConversationalAgent } from '@uipath/uipath-typescript/conversational-agent';

/**
 * OAuth PKCE session for the Coded App.
 *
 * Same pattern as the bootcamp lab tracker: `new UiPath()` with no arguments
 * reads clientId / scope / orgName / tenantName / baseUrl / redirectUri from
 * the <meta name="uipath:*"> tags (injected from uipath.json in dev, by the
 * platform in production). No tokens are ever handled or stored by app code.
 *
 * The signed-in user's email is resolved through the SDK's user-settings
 * endpoint and becomes the `ReviewedBy` value on approve / reject.
 */

export interface SignedInUser {
  email: string;
  name: string;
}

interface AuthContextValue {
  sdk: UiPath;
  user: SignedInUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Fatal auth error (login / callback failed). */
  error: string | null;
  /** Non-fatal: signed in, but the profile did not return an email (decisions are blocked). */
  profileWarning: string | null;
  login: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function messageOf(err: unknown, fallback: string): string {
  if (err instanceof UiPathError || err instanceof Error) return err.message || fallback;
  return fallback;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sdk] = useState(() => new UiPath());
  const [user, setUser] = useState<SignedInUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileWarning, setProfileWarning] = useState<string | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    // React StrictMode mounts effects twice in dev; the OAuth code is single-use.
    if (initialized.current) return;
    initialized.current = true;

    const initializeAuth = async () => {
      setIsLoading(true);
      setError(null);
      try {
        if (sdk.isInOAuthCallback()) {
          await sdk.completeOAuth();
          // Drop ?code=&state= so a refresh does not try to re-consume the code.
          window.history.replaceState({}, document.title, window.location.pathname);
        }

        const authenticated = sdk.isAuthenticated();
        setIsAuthenticated(authenticated);

        if (authenticated) {
          try {
            const conversationalAgent = new ConversationalAgent(sdk);
            const settings = await conversationalAgent.user.getSettings();
            if (settings.email) {
              setUser({ email: settings.email, name: settings.name || settings.email });
            } else {
              setUser(null);
              setProfileWarning(
                'Your UiPath profile did not return an email address, so ReviewedBy cannot be set. You can review invoices but not approve or reject them.'
              );
            }
          } catch (profileErr) {
            setUser(null);
            setProfileWarning(
              `Could not read your UiPath profile (${messageOf(profileErr, 'unknown error')}). You can review invoices but not approve or reject them.`
            );
          }
        }
      } catch (err) {
        setError(messageOf(err, 'Authentication failed'));
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [sdk]);

  const login = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Starts the PKCE redirect to UiPath sign-in; the page navigates away.
      await sdk.initialize();
    } catch (err) {
      setError(messageOf(err, 'Login failed'));
      setIsLoading(false);
    }
  };

  const logout = () => {
    sdk.logout();
    setIsAuthenticated(false);
    setUser(null);
    setError(null);
    setProfileWarning(null);
  };

  const value = useMemo(
    () => ({ sdk, user, isAuthenticated, isLoading, error, profileWarning, login, logout }),
    [sdk, user, isAuthenticated, isLoading, error, profileWarning]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
