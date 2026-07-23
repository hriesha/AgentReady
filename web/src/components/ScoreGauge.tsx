import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";

const GAUGE_FILL = "#065f46";
const GAUGE_TRACK = "#e7e5e4";

interface ScoreGaugeProps {
  score: number;
  label: string;
}

export default function ScoreGauge({ score, label }: ScoreGaugeProps) {
  const clamped = Math.min(100, Math.max(0, score));
  return (
    <div className="flex flex-col items-center">
      <div className="relative h-[140px] w-[200px]">
        <RadialBarChart
          width={200}
          height={140}
          cx={100}
          cy={104}
          innerRadius={72}
          outerRadius={88}
          startAngle={210}
          endAngle={-30}
          data={[{ value: clamped }]}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar
            dataKey="value"
            background={{ fill: GAUGE_TRACK }}
            cornerRadius={6}
            fill={GAUGE_FILL}
            isAnimationActive={false}
          />
        </RadialBarChart>
        <div className="absolute inset-x-0 top-[62px] text-center">
          <div className="text-3xl font-semibold text-stone-900">
            {clamped.toFixed(1)}
          </div>
          <div className="text-xs text-stone-500">of 100</div>
        </div>
      </div>
      <div className="mt-1 text-sm text-stone-600">{label}</div>
    </div>
  );
}
