import message from '@/assets/message.txt?raw';

/**
 * Screen 1 — gate page, shown only after a successful login (App.tsx never
 * renders it while unauthenticated or loading).
 *
 * The ONLY visual and copy sources are the lab assets: public/winner.png and
 * src/assets/message.txt (imported as raw text at build time). One button;
 * UiPath sign-in blue on cool neutrals; no headings, icons or extra copy.
 */
export function GatePage({ onContinue }: { onContinue: () => void }) {
  return (
    <main className="gate">
      <section className="gate-card">
        <img className="gate-image" src="./winner.png" alt="" width={1942} height={622} />
        <p className="gate-message">{message.trim()}</p>
        <button className="btn btn-blue" onClick={onContinue} autoFocus>
          Yes, I am winner
        </button>
      </section>
    </main>
  );
}
