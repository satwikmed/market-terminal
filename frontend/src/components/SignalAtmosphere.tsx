/**
 * Clearing-native atmosphere — the “light streak” idea from dark AI heroes,
 * rewritten for paper + ink + vermillion. Pure CSS, no WebGL.
 */
type Intensity = 'whisper' | 'hero';

const STREAKS = [
  { top: '6%', left: '-18%', width: '95%', rotate: -20, delay: '0s', duration: '16s', tone: 'accent' as const, thick: true },
  { top: '22%', left: '-6%', width: '110%', rotate: -15, delay: '-4s', duration: '20s', tone: 'accent' as const, thick: false },
  { top: '38%', left: '-20%', width: '100%', rotate: -22, delay: '-8s', duration: '18s', tone: 'ink' as const, thick: false },
  { top: '54%', left: '0%', width: '92%', rotate: -12, delay: '-2s', duration: '22s', tone: 'slate' as const, thick: false },
  { top: '70%', left: '-10%', width: '105%', rotate: -18, delay: '-11s', duration: '17s', tone: 'accent' as const, thick: true },
  { top: '14%', left: '25%', width: '80%', rotate: -10, delay: '-14s', duration: '24s', tone: 'ink' as const, thick: false },
  { top: '82%', left: '8%', width: '88%', rotate: -16, delay: '-6s', duration: '19s', tone: 'slate' as const, thick: false },
];

const TONE: Record<'accent' | 'ink' | 'slate', { fill: string; glow: string }> = {
  accent: {
    fill: 'linear-gradient(90deg, transparent 0%, rgba(255, 36, 0, 0.15) 12%, rgba(255, 36, 0, 0.85) 48%, rgba(255, 36, 0, 0.2) 78%, transparent 100%)',
    glow: '0 0 28px rgba(255, 36, 0, 0.55), 0 0 60px rgba(255, 36, 0, 0.25)',
  },
  ink: {
    fill: 'linear-gradient(90deg, transparent 0%, rgba(10, 11, 14, 0.08) 18%, rgba(10, 11, 14, 0.45) 50%, rgba(10, 11, 14, 0.1) 82%, transparent 100%)',
    glow: '0 0 16px rgba(10, 11, 14, 0.2)',
  },
  slate: {
    fill: 'linear-gradient(90deg, transparent 0%, rgba(0, 90, 140, 0.1) 15%, rgba(0, 90, 140, 0.5) 48%, rgba(0, 90, 140, 0.12) 80%, transparent 100%)',
    glow: '0 0 22px rgba(0, 90, 140, 0.35)',
  },
};

export function SignalAtmosphere({ intensity = 'hero' }: { intensity?: Intensity }) {
  const hero = intensity === 'hero';

  return (
    <div
      className={`signal-atmosphere pointer-events-none absolute inset-0 overflow-hidden ${
        hero ? 'opacity-100' : 'opacity-35'
      }`}
      aria-hidden
    >
      <div
        className={`signal-bloom signal-bloom--a absolute rounded-full blur-3xl ${
          hero ? 'w-[48rem] h-[48rem]' : 'w-[28rem] h-[28rem]'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(255, 36, 0, 0.28), transparent 68%)',
          top: '-22%',
          left: '-16%',
        }}
      />
      <div
        className={`signal-bloom signal-bloom--b absolute rounded-full blur-3xl ${
          hero ? 'w-[40rem] h-[40rem]' : 'w-[22rem] h-[22rem]'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(0, 90, 140, 0.18), transparent 70%)',
          bottom: '-24%',
          right: '-10%',
        }}
      />

      {STREAKS.map((s, i) => {
        const tone = TONE[s.tone];
        const height = hero ? (s.thick ? 3 : 1.5) : 1;
        return (
          <div
            key={i}
            className="absolute origin-left"
            style={{
              top: s.top,
              left: s.left,
              width: s.width,
              transform: `rotate(${s.rotate}deg)`,
              opacity: hero ? 1 : 0.5,
            }}
          >
            <span
              className="signal-streak block w-full rounded-full"
              style={{
                background: tone.fill,
                animationDelay: s.delay,
                animationDuration: s.duration,
                height: `${height}px`,
                boxShadow: hero ? tone.glow : 'none',
              }}
            />
          </div>
        );
      })}

      <div
        className="absolute inset-0"
        style={{
          background: hero
            ? 'linear-gradient(105deg, rgba(228, 230, 236, 0.35) 0%, rgba(228, 230, 236, 0.08) 38%, transparent 65%)'
            : 'linear-gradient(180deg, rgba(228, 230, 236, 0.4), transparent 45%)',
        }}
      />
    </div>
  );
}
