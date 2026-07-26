/**
 * Clearing-native atmosphere — the “light streak” idea from dark AI heroes,
 * rewritten for paper + ink + vermillion. Pure CSS, no WebGL.
 */
type Intensity = 'whisper' | 'hero';

const STREAKS = [
  { top: '8%', left: '-8%', width: '72%', rotate: -18, delay: '0s', duration: '22s', tone: 'accent' as const },
  { top: '28%', left: '12%', width: '88%', rotate: -14, delay: '-6s', duration: '28s', tone: 'ink' as const },
  { top: '52%', left: '-4%', width: '64%', rotate: -21, delay: '-11s', duration: '24s', tone: 'accent' as const },
  { top: '68%', left: '22%', width: '78%', rotate: -12, delay: '-3s', duration: '30s', tone: 'slate' as const },
  { top: '18%', left: '40%', width: '55%', rotate: -16, delay: '-15s', duration: '26s', tone: 'ink' as const },
];

const TONE: Record<'accent' | 'ink' | 'slate', string> = {
  accent: 'linear-gradient(90deg, transparent, rgba(255, 36, 0, 0.55), rgba(255, 36, 0, 0.08), transparent)',
  ink: 'linear-gradient(90deg, transparent, rgba(10, 11, 14, 0.22), rgba(10, 11, 14, 0.04), transparent)',
  slate: 'linear-gradient(90deg, transparent, rgba(0, 90, 140, 0.28), rgba(0, 90, 140, 0.05), transparent)',
};

export function SignalAtmosphere({ intensity = 'hero' }: { intensity?: Intensity }) {
  const hero = intensity === 'hero';

  return (
    <div
      className={`signal-atmosphere pointer-events-none absolute inset-0 overflow-hidden ${
        hero ? 'opacity-100' : 'opacity-40'
      }`}
      aria-hidden
    >
      <div
        className={`signal-bloom signal-bloom--a absolute rounded-full blur-3xl ${
          hero ? 'w-[42rem] h-[42rem]' : 'w-[28rem] h-[28rem]'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(255, 36, 0, 0.16), transparent 68%)',
          top: '-18%',
          left: '-12%',
        }}
      />
      <div
        className={`signal-bloom signal-bloom--b absolute rounded-full blur-3xl ${
          hero ? 'w-[36rem] h-[36rem]' : 'w-[22rem] h-[22rem]'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(0, 90, 140, 0.12), transparent 70%)',
          bottom: '-20%',
          right: '-8%',
        }}
      />

      {STREAKS.map((s, i) => (
        <div
          key={i}
          className="absolute origin-left"
          style={{
            top: s.top,
            left: s.left,
            width: s.width,
            transform: `rotate(${s.rotate}deg)`,
            opacity: hero ? 1 : 0.55,
          }}
        >
          <span
            className="signal-streak block w-full"
            style={{
              background: TONE[s.tone],
              animationDelay: s.delay,
              animationDuration: s.duration,
              height: hero ? (s.tone === 'accent' ? '2px' : '1px') : '1px',
              boxShadow:
                s.tone === 'accent'
                  ? '0 0 18px rgba(255, 36, 0, 0.35)'
                  : s.tone === 'slate'
                    ? '0 0 14px rgba(0, 90, 140, 0.2)'
                    : 'none',
            }}
          />
        </div>
      ))}

      <div
        className="absolute inset-0"
        style={{
          background: hero
            ? 'linear-gradient(105deg, rgba(228, 230, 236, 0.55) 0%, rgba(228, 230, 236, 0.15) 42%, transparent 70%)'
            : 'linear-gradient(180deg, rgba(228, 230, 236, 0.35), transparent 40%)',
        }}
      />
    </div>
  );
}
