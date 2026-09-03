import useAutoRefresh from '../hooks/useAutoRefresh';
import { getSeverityClass, getStatusClass } from '../utils/badges';

interface Incident {
  id: number;
  service_name: string;
  error_type: string;
  severity: string;
  status: string;
  occurrence_count: number;
  first_occurred_at: string;
  last_occurred_at: string;
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
    <div>
      <h2>Incidents</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Service</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Occurrence Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td>{incident.id}</td>
              <td>{incident.service_name}</td>
              <td><span className={getSeverityClass(incident.severity)}>{incident.severity}</span></td>
              <td><span className={getStatusClass(incident.status.toLowerCase())}>{incident.status}</span></td>
              <td>{incident.occurrence_count}</td>
              <td>{new Date(incident.first_occurred_at).toLocaleTimeString()}</td>
              <td>{new Date(incident.last_occurred_at).toLocaleTimeString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default IncidentsList;