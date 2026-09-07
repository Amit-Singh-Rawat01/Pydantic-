import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import useAutoRefresh from "../hooks/useAutoRefresh";

interface ServiceStat {
  service_name: string;
  count: number;
}

const fetchServiceStats = async (): Promise<ServiceStat[]> => {
  const response = await fetch("http://localhost:8000/stats/by-service");

  if (!response.ok) {
    throw new Error("Service stats request failed");
  }

  return response.json();
};

function FailingServicesChart() {
  const { data, loading, error } = useAutoRefresh(fetchServiceStats, 5000);
  const serviceStats = data ?? [];

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        Failing Services (Last 15 min)
      </h2>
      {loading && serviceStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-slate-500">
          Loading service stats...
        </p>
      ) : error && serviceStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-red-600">{error}</p>
      ) : serviceStats.length === 0 ? (
        <p className="h-62.5 content-center text-sm text-slate-500">
          No errors in the last 15 minutes.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <BarChart
            data={serviceStats}
            margin={{ top: 5, right: 12, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="service_name" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#ef4444" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

export default FailingServicesChart;