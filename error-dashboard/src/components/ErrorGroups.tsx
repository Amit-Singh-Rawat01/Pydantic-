import useAutoRefresh from "../hooks/useAutoRefresh";
import AsyncSection from "./AsyncSection";

type ErrorGroup = {
  fingerprint: string;
  service_name: string;
  error_type: string;
  count: number;
  last_seen: string;
  sample_message: string;
};

function ErrorGroups() {
  const { data, loading, error } = useAutoRefresh<ErrorGroup[]>(
    async () => {
      const response = await fetch("http://localhost:8000/error-groups");
      if (!response.ok) {
        throw new Error(`Error groups request failed with status ${response.status}`);
      }
      return response.json();
    },
    5000
  );

  const groups = data ?? [];
  const totalErrors = groups.reduce((sum, group) => sum + group.count, 0);
  const top = groups.slice(0, 10);

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold">Error Groups</h2>
      <p className="mb-3 text-sm text-gray-500">
        Pichhle 15 minute: {totalErrors} errors → {groups.length} groups
      </p>

      <AsyncSection
        loading={loading}
        error={error}
        isEmpty={groups.length === 0}
        emptyMessage="No error groups in the last 15 minutes."
      >
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Error type</th>
                <th className="px-3 py-2">Count</th>
                <th className="px-3 py-2">Last seen</th>
                <th className="px-3 py-2">Sample message</th>
              </tr>
            </thead>
            <tbody>
              {top.map((group) => (
                <tr key={`${group.service_name}-${group.fingerprint}`} className="border-t">
                  <td className="px-3 py-2 font-medium">{group.service_name}</td>
                  <td className="px-3 py-2">{group.error_type}</td>
                  <td className="px-3 py-2 font-semibold">{group.count}</td>
                  <td className="px-3 py-2">
                    {new Date(group.last_seen).toLocaleTimeString()}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-gray-600">
                    {group.sample_message}
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

export default ErrorGroups;
