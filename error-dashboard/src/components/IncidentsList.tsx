import useAutoRefresh from '../hooks/useAutoRefresh';
import { getSeverityClass, getStatusClass } from '../utils/badges';

interface Incident {
  id: number;
  fingerprint: string | null;
  service_name: string;
  error_type: string;
  sample_message: string | null;
  severity: string;
  status: string;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
}

function IncidentsList() {
  const { data, loading, error } = useAutoRefresh<{ items: Incident[] } | Incident[]>(
    () => fetch('http://localhost:8000/incidents').then(res => res.json()),
    5000
  );

  const incidents: Incident[] = Array.isArray(data) ? data : data?.items ?? [];

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Incidents</h2>
          <p className="mt-1 text-sm text-gray-500">
            Grouped problems by service, error type, and occurrence count
          </p>
        </div>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-600">
          {incidents.length} incident records
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="w-full min-w-[1080px] border-collapse text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
            <tr className="border-b border-gray-200">
              <th className="p-3">Service</th>
              <th className="p-3">Error</th>
              <th className="p-3">Severity</th>
              <th className="p-3">Status</th>
              <th className="p-3">Occurrences</th>
              <th className="p-3">First Seen</th>
              <th className="p-3">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((incident) => (
              <tr key={incident.id} className="border-b border-gray-100 last:border-b-0">
                <td className="p-3 font-semibold text-gray-900">{incident.service_name}</td>
                <td className="max-w-[360px] p-3">
                  <div className="font-medium text-gray-900">{incident.error_type}</div>
                  <div
                    className="truncate text-xs text-gray-500"
                    title={incident.sample_message ?? 'No sample message'}
                  >
                    {incident.sample_message ?? '-'}
                  </div>
                </td>
                <td className="p-3">
                  <span className={getSeverityClass(incident.severity)}>{incident.severity}</span>
                </td>
                <td className="p-3">
                  <span className={getStatusClass(incident.status.toLowerCase())}>{incident.status}</span>
                </td>
                <td className="p-3 font-semibold text-gray-900">{incident.occurrence_count}</td>
                <td className="whitespace-nowrap p-3 text-xs text-gray-500">
                  {new Date(incident.first_seen).toLocaleString()}
                </td>
                <td className="whitespace-nowrap p-3 text-xs text-gray-500">
                  {new Date(incident.last_seen).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default IncidentsList;