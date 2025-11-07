import { type FC, useCallback, useMemo, useState } from "react";
import {
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  LabelList
} from "recharts";

export interface SeriesConfig {
  dataKey: string;
  color: string;
  name: string;
}

export interface LineChartProps {
  data: Record<string, string | number | null>[];
  xKey: string;
  series: SeriesConfig[];
}

const LineChart: FC<LineChartProps> = ({ data, xKey, series }) => {
  const [showLabels, setShowLabels] = useState(false);

  const yDomain = useMemo<[number | "auto", number | "auto"]>(() => {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    data.forEach((entry) => {
      series.forEach(({ dataKey }) => {
        const rawValue = entry[dataKey];
        const value = typeof rawValue === "number" ? rawValue : rawValue != null ? Number(rawValue) : null;
        if (value != null && Number.isFinite(value)) {
          min = Math.min(min, value);
          max = Math.max(max, value);
        }
      });
    });

    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return ["auto", "auto"];
    }

    if (min === max) {
      const padding = Math.abs(min) * 0.05 || 1;
      return [min - padding, max + padding];
    }

    const range = max - min;
    const padding = range * 0.1;
    return [min - padding, max + padding];
  }, [data, series]);

  const formatValue = useCallback((value: number) => {
    const abs = Math.abs(value);
    const fractionDigits = abs >= 1000 ? 0 : abs >= 100 ? 1 : 2;
    return value.toLocaleString(undefined, {
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits
    });
  }, []);

  const renderLabel = useCallback(
    (props: { value?: number | string; x?: number; y?: number }) => {
      if (!showLabels) return null;

      const { value, x = 0, y = 0 } = props;
      if (value == null) return null;
      const numericValue = typeof value === "number" ? value : Number(value);
      if (!Number.isFinite(numericValue)) return null;

      return (
        <text x={x} y={y - 10} fill="#cbd5f5" fontSize={11} textAnchor="middle">
          {formatValue(numericValue)}
        </text>
      );
    },
    [formatValue, showLabels]
  );

  return (
    <div className="chart-block">
      <div className="chart-controls">
        <button
          type="button"
          className="chart-toggle"
          onClick={() => setShowLabels((prev) => !prev)}
          aria-pressed={showLabels}
        >
          {showLabels ? "隱藏數值" : "顯示數值"}
        </button>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <RechartsLineChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(148, 163, 184, 0.2)" />
          <XAxis dataKey={xKey} stroke="#94a3b8" tickLine={false} axisLine={false} />
          <YAxis
            stroke="#94a3b8"
            tickLine={false}
            axisLine={false}
            domain={yDomain}
            tickFormatter={(value) => (typeof value === "number" ? formatValue(value) : value)}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              borderRadius: 12,
              border: "1px solid rgba(148,163,184,0.2)",
              color: "#e2e8f0"
            }}
            formatter={(value: number | string) => {
              if (typeof value === "number") return formatValue(value);
              const numericValue = Number(value);
              return Number.isFinite(numericValue) ? formatValue(numericValue) : value;
            }}
          />
          <Legend />
          {series.map(({ dataKey, color, name }) => (
            <Line
              key={dataKey}
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2.4}
              dot={showLabels ? { r: 3 } : false}
              activeDot={{ r: 4 }}
              name={name}
            >
              <LabelList content={renderLabel} />
            </Line>
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default LineChart;
