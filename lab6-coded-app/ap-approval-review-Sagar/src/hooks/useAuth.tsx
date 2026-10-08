import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { UiPath, UiPathError } from '@uipath/uipath-typescript/core';
import { ConversationalAgent } from '@uipath/uipath-typescript/conversational-agent';

export interface SignedInUser {
  email: string;
  name: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  sdk: UiPath;
  /** Signed-in user; its email becomes ReviewedBy on approve / reject. */
  user: SignedInUser | null;
  /** Non-fatal: signed in, but no email could be resolved (decisions are blocked). */
  profileWarning: string | null;
  login: () => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function messageOf(err: unknown, fallback: string): string {
  if (err instanceof UiPathError || err instanceof Error) return err.message || fallback;
  return fallback;
}

/**
 * Reads only the `email` claim from the SDK's access token, in memory.
 * The token itself is never stored, logged or rendered.
 */
function emailFromToken(sdk: UiPath): string | null {
  try {
    const payload = sdk.getToken()?.split('.')[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return typeof json.email === 'string' && json.email ? json.email : null;
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<SignedInUser | null>(null);
  const [profileWarning, setProfileWarning] = useState<string | null>(null);
  // `new UiPath()` reads clientId/orgName/tenantName/baseUrl/scope/redirectUri
  // from <meta name="uipath:*"> tags. The uipathCodedApps() Vite plugin
  // injects them locally from uipath.json; the platform injects them in prod.
  const [sdk] = useState<UiPath>(() => new UiPath());
  const didInit = useRef(false);

  useEffect(() => {
    // Guard against React Strict Mode's double-invocation in dev.
    // OAuth authorization codes are single-use — calling completeOAuth()
    // twice would fail the second time with "Authentication failed".
    if (didInit.current) return;
    didInit.current = true;

    const resolveUser = async () => {
      // Primary: the user-settings endpoint (scope OR.Users.Read).
      try {
        const settings = await new ConversationalAgent(sdk).user.getSettings();
        if (settings.email) {
          setUser({ email: settings.email, name: settings.name || settings.email });
          return;
        }
      } catch {
        /* fall back to the token claim below */
      }
      // Fallback: the email claim of the SDK token.
      const email = emailFromToken(sdk);
      if (email) {
        setUser({ email, name: email });
        return;
      }
      setUser(null);
      setProfileWarning('Your UiPath profile did not return an email address, so ReviewedBy cannot be set. You can review invoices but not approve or reject them.');
    };

    const initializeAuth = async () => {
      setIsLoading(true);
      setError(null);
      try {
        if (sdk.isInOAuthCallback()) {
          await sdk.completeOAuth();
          // Strip OAuth params from the URL so a refresh doesn't try to
          // re-consume the (now-invalid) code.
          window.history.replaceState({}, document.title, window.location.pathname);
        }
        const authenticated = sdk.isAuthenticated();
        setIsAuthenticated(authenticated);
        if (authenticated) await resolveUser();
      } catch (err) {
        console.error('Authentication failed:', err);
        setError(messageOf(err, 'Authentication failed'));
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
      await sdk.initialize();
    } catch (err) {
      setError(messageOf(err, 'Login failed'));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    sdk.logout();
    setIsAuthenticated(false);
    setUser(null);
    setProfileWarning(null);
    setError(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, sdk, user, profileWarning, login, logout, error }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
