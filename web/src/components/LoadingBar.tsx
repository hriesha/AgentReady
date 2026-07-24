import { useEffect, useState } from "react";

const BAR_FILL = "#065f46";
const CEILING = 95;
const TICK_MS = 200;
const MESSAGE_MS = 3500;

interface LoadingBarProps {
  title: string;
  messages: string[];
}

const FUR = "#a8a29e";
const FUR_DARK = "#78716c";
const BELLY = "#e7e5e4";
const FEATURE = "#44403c";
const WATER = "#d6d3d1";

/**
 * An otter floating on its back holding a product box, bobbing on drifting
 * water. The ripple path is one wavelength wider than it travels, so the loop
 * meets itself and never visibly snaps back.
 */
function FloatingOtter() {
  return (
    <svg
      viewBox="0 0 160 84"
      aria-hidden="true"
      className="mx-auto h-24 w-44 overflow-hidden"
    >
      <g className="origin-center animate-bob motion-reduce:animate-none">
        <path
          d="M34 48 q-16 3 -22 -7 q12 6 22 1 z"
          fill={FUR_DARK}
        />
        <ellipse cx="46" cy="35" rx="5" ry="3.4" fill={FUR_DARK} />
        <ellipse cx="57" cy="33" rx="5" ry="3.4" fill={FUR_DARK} />
        <ellipse cx="70" cy="48" rx="33" ry="13.5" fill={FUR} />
        <ellipse cx="72" cy="50" rx="25" ry="9" fill={BELLY} />

        <g>
          <rect x="62" y="27" width="21" height="17" rx="2.5" fill={BAR_FILL} />
          <line
            x1="72.5"
            y1="27"
            x2="72.5"
            y2="44"
            stroke={BELLY}
            strokeWidth="1.4"
          />
          <line
            x1="62"
            y1="33.5"
            x2="83"
            y2="33.5"
            stroke={BELLY}
            strokeWidth="1.4"
          />
          <path
            className="animate-twinkle motion-reduce:animate-none"
            d="M88 24 l1.6 3.6 l3.6 1.6 l-3.6 1.6 l-1.6 3.6 l-1.6 -3.6 l-3.6 -1.6 l3.6 -1.6 z"
            fill={FUR_DARK}
          />
        </g>
        <ellipse cx="60" cy="41" rx="4.6" ry="3.6" fill={FUR_DARK} />
        <ellipse cx="85" cy="41" rx="4.6" ry="3.6" fill={FUR_DARK} />

        <circle cx="106" cy="28" r="4.4" fill={FUR_DARK} />
        <circle cx="121" cy="28" r="4.4" fill={FUR_DARK} />
        <circle cx="113" cy="40" r="13.5" fill={FUR} />
        <ellipse cx="113" cy="45" rx="7.5" ry="5.4" fill={BELLY} />
        <circle cx="108" cy="36" r="1.9" fill={FEATURE} />
        <circle cx="118" cy="36" r="1.9" fill={FEATURE} />
        <ellipse cx="113" cy="41.5" rx="2.4" ry="1.7" fill={FEATURE} />
        <g stroke={FUR_DARK} strokeWidth="0.9" strokeLinecap="round">
          <line x1="105" y1="44" x2="97" y2="42.5" />
          <line x1="105" y1="46.5" x2="97" y2="47.5" />
          <line x1="121" y1="44" x2="129" y2="42.5" />
          <line x1="121" y1="46.5" x2="129" y2="47.5" />
        </g>
      </g>

      <g
        className="animate-ripple motion-reduce:animate-none"
        stroke={WATER}
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      >
        <path d="M-40 68 q10 -5 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0" />
        <path
          d="M-40 76 q10 -5 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0"
          opacity="0.6"
        />
      </g>
    </svg>
  );
}

/**
 * A bar for waits whose length we cannot know, such as the free host waking
 * from sleep. It eases toward a ceiling instead of claiming real progress, so
 * it always looks alive and never stalls at a number it cannot pass.
 */
export default function LoadingBar({ title, messages }: LoadingBarProps) {
  const [percent, setPercent] = useState(4);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setPercent((current) => current + (CEILING - current) * 0.015);
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (step >= messages.length - 1) return;
    const timer = window.setTimeout(
      () => setStep((current) => current + 1),
      MESSAGE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [step, messages.length]);

  return (
    <div className="mx-auto max-w-xl">
      <FloatingOtter />
      <div className="mt-4 flex items-baseline justify-between text-sm text-stone-600">
        <span>{title}</span>
        <span aria-hidden className="tabular-nums text-stone-500">
          {Math.round(percent)}%
        </span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-stone-200">
        <div
          className="relative h-2 overflow-hidden rounded-full transition-[width] duration-200 ease-linear"
          style={{ width: `${percent}%`, backgroundColor: BAR_FILL }}
        >
          <div className="absolute inset-y-0 w-1/3 animate-shimmer bg-white/30 motion-reduce:hidden" />
        </div>
      </div>
      <div role="status" className="mt-3 text-sm text-stone-500">
        <span key={step} className="inline-block animate-fadeIn">
          {messages[step]}
        </span>
      </div>
    </div>
  );
}
