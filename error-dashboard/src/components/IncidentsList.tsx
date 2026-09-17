import { useState } from 'react';
import useAutoRefresh from '../hooks/useAutoRefresh';
import { getSeverityClass, getStatusClass } from '../utils/badges';
import AsyncSection from './AsyncSection';

interface Incident {
  id: number;
  fingerprint: string | null;
  service_name: string;
  error_type: string;
  sample_message: string | null;
  severity: string;
  status: 'OPEN' | 'RESOLVED';
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
}

type StatusFilter = 'ALL' | 'OPEN' | 'RESOLVED';

function IncidentsList() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const { data, loading, error } = useAutoRefresh<{ items: Incident[] } | Incident[]>(
    async () => {
      const response = await fetch('http://localhost:8000/incidents');
      if (!response.ok) {
        throw new Error(`Incidents request failed with status ${response.status}`);
      }
      return response.json();
    },
    5000
  );

  const incidents: Incident[] = Array.isArray(data) ? data : data?.items ?? [];
  const filteredIncidents = incidents.filter((incident) => {
    if (statusFilter === 'ALL') return true;
    return incident.status === statusFilter;
  });
  const sortedIncidents = [...filteredIncidents].sort((a, b) => {
    if (a.status === b.status) return 0;
    return a.status === 'OPEN' ? -1 : 1;
  });

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

      <div className="mb-2 flex flex-wrap gap-2">
        {(['ALL', 'OPEN', 'RESOLVED'] as const).map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(status)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              statusFilter === status
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status}
          </button>
        ))}
      </div>
      <p className="mb-4 text-sm text-gray-500">
        Showing {filteredIncidents.length} of {incidents.length} incidents
      </p>

      <AsyncSection
        loading={loading}
        error={error}
        isEmpty={filteredIncidents.length === 0}
        emptyMessage={
          statusFilter === 'ALL'
            ? 'No incidents detected yet.'
            : `No ${statusFilter.toLowerCase()} incidents found.`
        }
      >
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
              {sortedIncidents.map((incident) => (
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
      </AsyncSection>
    </div>
  );
}

export default IncidentsList;