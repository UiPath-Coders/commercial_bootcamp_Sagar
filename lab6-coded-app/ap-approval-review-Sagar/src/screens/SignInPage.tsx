/** Shown before login: a single centered "Sign in with UiPath" button. */
export function SignInPage({
  onSignIn,
  isLoading,
  error,
}: {
  onSignIn: () => void;
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gradient-to-b from-uipath-50 to-slate-50">
      <div className="grid justify-items-center gap-3">
        <button
          type="button"
          onClick={onSignIn}
          disabled={isLoading}
          aria-busy={isLoading}
          className="min-h-11 px-6 rounded-md bg-uipath-600 text-white text-[15px] font-medium shadow-sm transition-colors hover:bg-uipath-700 active:bg-uipath-800 disabled:opacity-60 disabled:cursor-wait focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-uipath-500"
        >
          Sign in with UiPath
        </button>
        {error && (
          <p role="alert" className="max-w-sm text-center text-sm text-red-700">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}
