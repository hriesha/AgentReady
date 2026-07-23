const NOW_FILL = "#065f46";
const LIFT_FILL = "#6ee7b7";

interface ScoreBarProps {
  value: number;
  projected?: number | null;
}

export default function ScoreBar({ value, projected }: ScoreBarProps) {
  const now = Math.min(100, Math.max(0, value));
  const after = projected == null ? now : Math.min(100, Math.max(0, projected));
  const lift = Math.max(0, after - now);
  return (
    <div className="mt-1 flex h-1.5 w-24 gap-[2px] overflow-hidden rounded-full bg-stone-200">
      <div
        className="h-full"
        style={{ width: `${now}%`, backgroundColor: NOW_FILL }}
      />
      {lift > 0 && (
        <div
          className="h-full"
          style={{ width: `${lift}%`, backgroundColor: LIFT_FILL }}
        />
      )}
    </div>
  );
}
