import useAutoRefresh from "../hooks/useAutoRefresh";
import AsyncSection from "./AsyncSection";
import { statusColor } from "./statusStyles";

type AnomalyEvent = {
  id: number;
  service_name: string;
  old_status: string | null;
  new_status: string;
  z_score: number | null;
  detected_at: string;
};

function AnomalyEvents() {
  const { data: events, loading, error } = useAutoRefresh<AnomalyEvent[]>(
    async () => {
      const response = await fetch("http://localhost:8000/anomaly-events");
      if (!response.ok) {
        throw new Error(`Anomaly events request failed with status ${response.status}`);
      }
      return response.json();
    },
    5000
  );

  const anomalyEvents = events ?? [];
  const latest = [...anomalyEvents].sort((a, b) => b.id - a.id).slice(0, 20);

  return (
    <div className="p-6">
      <h2 className="mb-4 text-2xl font-bold">
        Anomaly Events ({anomalyEvents.length})
      </h2>

      <AsyncSection
        loading={loading}
        error={error}
        isEmpty={anomalyEvents.length === 0}
        emptyMessage="No anomaly events yet."
      >
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Status badlav</th>
                <th className="px-3 py-2">Z-Score</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((event) => (
                <tr key={event.id} className="border-t">
                  <td className="whitespace-nowrap px-3 py-2">
                    {new Date(event.detected_at).toLocaleTimeString()}
                  </td>
                  <td className="px-3 py-2 font-medium">{event.service_name}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span
                      className={`rounded px-2 py-1 text-xs ${statusColor(event.old_status ?? "START")}`}
                    >
                      {event.old_status ?? "START"}
                    </span>
                    {" → "}
                    <span
                      className={`rounded px-2 py-1 text-xs ${statusColor(event.new_status)}`}
                    >
                      {event.new_status}
                    </span>
                  </td>
                  <td className="px-3 py-2">{event.z_score?.toFixed(1) ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncSection>
    </div>
  );
}

export default AnomalyEvents;
