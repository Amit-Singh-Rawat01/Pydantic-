import useAutoRefresh from "../hooks/useAutoRefresh";
import AsyncSection from "./AsyncSection";
import { borderColor, statusColor } from "./statusStyles";

type ServiceHealth = {
  service: string;
  status: string;
  z_score: number | null;
  current: number | null;
};

type TopGroup = {
  service_name: string;
  error_type: string;
  count: number;
};

function ServiceHealth() {
  const { data: services, loading, error } = useAutoRefresh<ServiceHealth[]>(
    async () => {
      const response = await fetch("http://localhost:8000/metrics/anomaly-score");
      if (!response.ok) {
        throw new Error(`Service health request failed with status ${response.status}`);
      }
      return response.json();
    },
    5000
  );
  const { data: groups } = useAutoRefresh<TopGroup[]>(
    async () => {
      const response = await fetch("http://localhost:8000/error-groups?minutes=5");
      if (!response.ok) {
        throw new Error(`Error groups request failed with status ${response.status}`);
      }
      return response.json();
    },
    5000
  );

  const serviceList = services ?? [];
  const sorted = [...serviceList].sort((a, b) =>
    a.service.localeCompare(b.service)
  );
  const topErrorOf = (name: string) =>
    groups?.find((group) => group.service_name === name);

  return (
    <section className="p-6">
      <h2 className="mb-4 text-2xl font-bold">Service Health</h2>

      <AsyncSection
        loading={loading}
        error={error}
        isEmpty={serviceList.length === 0}
        emptyMessage="No service health data yet."
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {sorted.map((service) => {
            const top =
              service.status === "ANOMALY" || service.status === "WARNING"
                ? topErrorOf(service.service)
                : undefined;

            return (
              <div
                key={service.service}
                className={`rounded-lg border-2 p-4 ${borderColor(service.status)}`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{service.service}</h3>
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${statusColor(service.status)} ${
                      service.status === "ANOMALY" ? "animate-pulse" : ""
                    }`}
                  >
                    {service.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  Abhi: {service.current ?? "-"} errors/min
                </p>
                <p className="text-sm text-gray-600">
                  Z-Score: {service.z_score?.toFixed(1) ?? "-"}
                </p>
                {top && (
                  <p
                    className={`mt-3 rounded px-2 py-1 text-sm ${statusColor(service.status)}`}
                  >
                    Hint: {top.error_type} ({top.count} errors, last 5 min)
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </AsyncSection>
    </section>
  );
}

export default ServiceHealth;
