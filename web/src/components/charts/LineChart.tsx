import type { FC } from "react";
import { Line, LineChart as RechartsLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend } from "recharts";

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
  return (
    <ResponsiveContainer width="100%" height={320}>
      <RechartsLineChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="rgba(148, 163, 184, 0.2)" />
        <XAxis dataKey={xKey} stroke="#94a3b8" tickLine={false} axisLine={false} />
        <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ background: "#0f172a", borderRadius: 12, border: "1px solid rgba(148,163,184,0.2)", color: "#e2e8f0" }} />
        <Legend />
        {series.map(({ dataKey, color, name }) => (
          <Line key={dataKey} type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.4} dot={false} name={name} />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
};

export default LineChart;
