import useAutoRefresh from "../hooks/useAutoRefresh";

interface Stats {
  total_errors: number;
  errors_per_minute: number;
  active_incidents: number;
  system_health: "HEALTHY" | "WARNING" | "CRITICAL";
}

const fetchStats = async (): Promise<Stats> => {
  const response = await fetch("http://localhost:8000/stats");

  if (!response.ok) {
    throw new Error("Stats request failed");
  }

  return response.json();
};

function StatsCards() {
  const { data: stats, loading, error } = useAutoRefresh<Stats>(
    fetchStats,
    5000
  );

  if (loading) return <p className="p-6">Loading stats...</p>;
  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!stats) return null;

  const healthColor =
    stats.system_health === "HEALTHY"
      ? "bg-green-50 text-green-700 border-green-200"
      : stats.system_health === "WARNING"
        ? "bg-yellow-50 text-yellow-700 border-yellow-200"
        : "bg-red-50 text-red-700 border-red-200";

  return (
    <div className="grid grid-cols-2 gap-4 p-6 pb-0 md:grid-cols-4">
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-blue-700">
        <p className="text-sm font-medium">Total Errors</p>
        <p className="mt-1 text-2xl font-bold">{stats.total_errors}</p>
      </div>
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-yellow-700">
        <p className="text-sm font-medium">Errors / Min</p>
        <p className="mt-1 text-2xl font-bold">{stats.errors_per_minute}</p>
      </div>
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        <p className="text-sm font-medium">Active Incidents</p>
        <p className="mt-1 text-2xl font-bold">{stats.active_incidents}</p>
      </div>
      <div className={`rounded-lg border p-4 ${healthColor}`}>
        <p className="text-sm font-medium">System Health</p>
        <p className="mt-1 text-2xl font-bold">{stats.system_health}</p>
      </div>
    </div>
  );
}

export default StatsCards;
