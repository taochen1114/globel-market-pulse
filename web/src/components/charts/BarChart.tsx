import type { FC } from "react";
import { Bar, BarChart as RechartsBarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface BarChartProps {
  data: Record<string, number | string | null>[];
  xKey: string;
  dataKey: string;
  label: string;
}

const BarChart: FC<BarChartProps> = ({ data, xKey, dataKey, label }) => {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <RechartsBarChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="rgba(148, 163, 184, 0.2)" />
        <XAxis dataKey={xKey} stroke="#94a3b8" tickLine={false} axisLine={false} />
        <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ background: "#0f172a", borderRadius: 12, border: "1px solid rgba(148,163,184,0.2)", color: "#e2e8f0" }} />
        <Legend />
        <Bar dataKey={dataKey} name={label} fill="#38bdf8" radius={[10, 10, 0, 0]} />
      </RechartsBarChart>
    </ResponsiveContainer>
  );
};

export default BarChart;
