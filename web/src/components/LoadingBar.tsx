import { useEffect, useState } from "react";

const BAR_FILL = "#065f46";
const CEILING = 95;
const TICK_MS = 200;
const MESSAGE_MS = 3500;

interface LoadingBarProps {
  title: string;
  messages: string[];
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
      <div className="flex items-baseline justify-between text-sm text-stone-600">
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
