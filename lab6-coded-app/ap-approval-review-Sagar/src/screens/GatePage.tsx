import winner from '@/assets/winner.png';
import message from '@/assets/message.txt?raw';

/**
 * Screen 1: gate page, shown only after a successful login.
 * The only visual and copy sources are src/assets/winner.png and
 * src/assets/message.txt (imported as raw text at build time).
 */
export function GatePage({ onContinue }: { onContinue: () => void }) {
  return (
    <main className="min-h-screen grid place-items-center p-4 sm:p-8 bg-[radial-gradient(1200px_600px_at_50%_-10%,rgba(0,103,223,0.18),transparent_60%),linear-gradient(180deg,#eef3fb_0%,#f8fafc_100%)]">
      <section className="w-full max-w-4xl grid justify-items-center gap-6 sm:gap-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-12 text-center shadow-[0_2px_6px_rgba(15,23,42,0.08),0_28px_60px_-24px_rgba(15,23,42,0.35)]">
        <img
          src={winner}
          alt=""
          width={1942}
          height={622}
          className="w-full max-w-3xl h-auto rounded-xl border border-uipath-100 bg-uipath-50"
        />
        <p className="max-w-[62ch] whitespace-pre-line text-lg sm:text-2xl leading-relaxed font-medium text-slate-800">
          {message.trim()}
        </p>
        <button
          type="button"
          onClick={onContinue}
          autoFocus
          className="min-h-11 px-6 rounded-md bg-uipath-600 text-white text-[15px] font-medium shadow-sm transition-colors hover:bg-uipath-700 active:bg-uipath-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-uipath-500"
        >
          Yes, I am winner
        </button>
      </section>
    </main>
  );
}
