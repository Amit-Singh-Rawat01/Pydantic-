import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import useAutoRefresh from "../hooks/useAutoRefresh";

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#22c55e",
  MEDIUM: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

interface SeverityData {
  severity: string;
  count: number;
}

const fetchSeverityStats = async (): Promise<SeverityData[]> => {
  const response = await fetch(
    "http://localhost:8000/stats/severity-breakdown"
  );

  if (!response.ok) {
    throw new Error("Severity stats request failed");
  }

  return response.json();
};

function SeverityChart() {
  const { data, loading, error } = useAutoRefresh(fetchSeverityStats, 5000);
  const severityStats = data ?? [];

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        Severity Breakdown (Last 15 min)
      </h2>
      {loading && severityStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-slate-500">
          Loading severity stats...
        </p>
      ) : error && severityStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-red-600">{error}</p>
      ) : severityStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-slate-500">
          No errors in the last 15 minutes.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={severityStats}
              dataKey="count"
              nameKey="severity"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={({ name, percent }) =>
                `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
              }
            >
              {severityStats.map((entry) => (
                <Cell
                  key={entry.severity}
                  fill={SEVERITY_COLORS[entry.severity] ?? "#94a3b8"}
                />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

export default SeverityChart;