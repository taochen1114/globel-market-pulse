import type { FC } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as RechartsLineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
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
  height?: number;
  showLegend?: boolean;
}

const INDEX_KEY = "__index__";

const LineChart: FC<LineChartProps> = ({ data, xKey, series, height = 320, showLegend = true }) => {
  const processedData = useMemo(() => {
    return data.map((item, index) => {
      const normalized: Record<string, string | number | null> = { ...item };

      series.forEach(({ dataKey }) => {
        const rawValue = item[dataKey];
        if (typeof rawValue === "string") {
          const parsed = Number(rawValue.replace(/,/g, ""));
          if (!Number.isNaN(parsed)) {
            normalized[dataKey] = parsed;
          }
        }
      });

      return {
        ...normalized,
        [INDEX_KEY]: index,
      };
    });
  }, [data, series]);

  const getYDomain = useCallback(
    (from: number, to: number): [number, number] => {
      if (!processedData.length) {
        return [0, 0];
      }

      const start = Math.max(0, Math.min(from, to));
      const end = Math.min(processedData.length - 1, Math.max(from, to));

      let min = Number.POSITIVE_INFINITY;
      let max = Number.NEGATIVE_INFINITY;

      for (let index = start; index <= end; index += 1) {
        const entry = processedData[index];

        series.forEach(({ dataKey }) => {
          const value = entry[dataKey];
          if (typeof value === "number" && Number.isFinite(value)) {
            min = Math.min(min, value);
            max = Math.max(max, value);
          }
        });
      }

      if (!Number.isFinite(min) || !Number.isFinite(max)) {
        return [0, 0];
      }

      if (min === max) {
        const padding = min === 0 ? 1 : Math.abs(min) * 0.1;
        return [min - padding, max + padding];
      }

      const padding = (max - min) * 0.08;
      return [min - padding, max + padding];
    },
    [processedData, series],
  );

  const initialXDomain = useMemo<[number, number]>(() => {
    if (!processedData.length) {
      return [0, 0];
    }
    return [0, processedData.length - 1];
  }, [processedData]);

  const initialYDomain = useMemo<[number, number]>(() => {
    return getYDomain(initialXDomain[0], initialXDomain[1]);
  }, [getYDomain, initialXDomain]);

  const [xDomain, setXDomain] = useState<[number, number]>(initialXDomain);
  const [yDomain, setYDomain] = useState<[number, number]>(initialYDomain);
  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null);

  useEffect(() => {
    setXDomain(initialXDomain);
    setYDomain(initialYDomain);
  }, [initialXDomain, initialYDomain]);

  const isZoomed =
    xDomain[0] !== initialXDomain[0] ||
    xDomain[1] !== initialXDomain[1] ||
    yDomain[0] !== initialYDomain[0] ||
    yDomain[1] !== initialYDomain[1];

  const resetZoom = () => {
    setXDomain(initialXDomain);
    setYDomain(initialYDomain);
    setRefAreaLeft(null);
    setRefAreaRight(null);
  };

  const handleMouseDown = (state: any) => {
    if (state?.activeLabel == null) {
      return;
    }
    setRefAreaLeft(state.activeLabel);
    setRefAreaRight(state.activeLabel);
  };

  const handleMouseMove = (state: any) => {
    if (refAreaLeft == null || state?.activeLabel == null) {
      return;
    }
    setRefAreaRight(state.activeLabel);
  };

  const applyZoom = () => {
    if (refAreaLeft == null || refAreaRight == null || refAreaLeft === refAreaRight) {
      setRefAreaLeft(null);
      setRefAreaRight(null);
      return;
    }

    const from = Math.max(0, Math.min(refAreaLeft, refAreaRight));
    const to = Math.min(processedData.length - 1, Math.max(refAreaLeft, refAreaRight));

    if (from === to) {
      setRefAreaLeft(null);
      setRefAreaRight(null);
      return;
    }

    setXDomain([from, to]);
    setYDomain(getYDomain(from, to));
    setRefAreaLeft(null);
    setRefAreaRight(null);
  };

  const handleMouseUp = () => {
    applyZoom();
  };

  const handleMouseLeave = () => {
    if (refAreaLeft != null && refAreaRight != null) {
      applyZoom();
    } else {
      setRefAreaLeft(null);
      setRefAreaRight(null);
    }
  };

  const formatLabel = useCallback(
    (index: number) => {
      const item = processedData[Math.round(index)];
      const label = item?.[xKey];
      if (label == null) {
        return String(index);
      }
      return typeof label === "number" ? label.toString() : String(label);
    },
    [processedData, xKey],
  );

  if (!processedData.length) {
    return null;
  }

  return (
    <div className="line-chart-container" style={{ height }}>
      {isZoomed ? (
        <button type="button" className="chart-reset-button" onClick={resetZoom}>
          重設縮放
        </button>
      ) : null}
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart
          data={processedData}
          margin={{ top: 24, right: 24, bottom: 16, left: 8 }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        >
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(148, 163, 184, 0.25)" />
          <XAxis
            dataKey={INDEX_KEY}
            type="number"
            domain={xDomain}
            allowDataOverflow
            tickFormatter={formatLabel}
            stroke="#94a3b8"
            tickLine={false}
            axisLine={false}
            minTickGap={12}
          />
          <YAxis
            type="number"
            domain={yDomain}
            allowDataOverflow
            stroke="#94a3b8"
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              borderRadius: 12,
              border: "1px solid rgba(148,163,184,0.25)",
              color: "#e2e8f0",
            }}
            labelFormatter={(label) => formatLabel(Number(label))}
          />
          {showLegend && <Legend />}
          {refAreaLeft != null && refAreaRight != null ? (
            <ReferenceArea
              x1={Math.min(refAreaLeft, refAreaRight)}
              x2={Math.max(refAreaLeft, refAreaRight)}
              strokeOpacity={0.3}
            />
          ) : null}
          {series.map(({ dataKey, color, name }) => (
            <Line
              key={dataKey}
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot
              activeDot={{ r: 5 }}
              name={name}
              isAnimationActive={false}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default LineChart;
