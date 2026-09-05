import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import useAutoRefresh from "../hooks/useAutoRefresh";

interface TimelinePoint {
  minute: string;
  count: number;
}

interface TimelineResponse {
  timeline: TimelinePoint[];
}

const fetchTimeline = async (): Promise<TimelineResponse> => {
  const response = await fetch("http://localhost:8000/stats/timeline");

  if (!response.ok) {
    throw new Error("Timeline request failed");
  }

  return response.json();
};

function ErrorTimelineChart() {
  const { data, loading, error } = useAutoRefresh(fetchTimeline, 5000);
  const timeline = data?.timeline ?? [];

  return (
    <section className="mx-6 mt-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        Error Timeline (Last 15 min)
      </h2>
      {loading && timeline.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-slate-500">
          Loading timeline...
        </p>
      ) : error && timeline.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-red-600">{error}</p>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={timeline} margin={{ top: 5, right: 12, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="minute" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

export default ErrorTimelineChart;
