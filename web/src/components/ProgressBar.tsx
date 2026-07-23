const BAR_FILL = "#2a78d6";

interface ProgressBarProps {
  current: number;
  total: number;
  label: string;
}

export default function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm text-slate-600">
        <span>{label}</span>
        <span>
          {current} of {total}
        </span>
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
        <div
          className="h-2 rounded-full transition-all duration-300"
          style={{ width: `${percent}%`, backgroundColor: BAR_FILL }}
        />
      </div>
    </div>
  );
}
