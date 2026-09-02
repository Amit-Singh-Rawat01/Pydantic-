import { useEffect, useState } from "react";

interface ErrorItem {
  id: number;
  service_name: string;
  error_type: string;
  message: string;
  severity: string;
  occurred_at: string;
}

function ErrorsList() {
  const [errors, setErrors] = useState<ErrorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    const fetchErrors = () => {
      fetch("http://localhost:8000/errors")
        .then((response) => response.json())
        .then((data) => {
          console.log("BACKEND DATA:", data);
          console.log("ERRORS ARRAY:", data.errors);

          console.log("UPDATING UI:", data.errors.length, new Date().toLocaleTimeString());

          setErrors(data.errors);
          setLastUpdated(new Date());
          setLoading(false);
        })
        .catch((error) => {
          console.error("FETCH ERROR:", error);
          setLoading(false);
        });
    };

    // Pehli baar immediately fetch
    fetchErrors();

    // Har 5 second mein fetch
    const interval = setInterval(() => {
      fetchErrors();
    }, 5000);

    // Component unmount hone par interval band
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <p className="p-6">Loading...</p>;
  }

  const severityColor: Record<string, string> = {
    LOW: "bg-blue-100 text-blue-700",
    MEDIUM: "bg-yellow-100 text-yellow-700",
    HIGH: "bg-orange-100 text-orange-700",
    CRITICAL: "bg-red-100 text-red-700",
  };

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-bold">
        Live Errors
      </h1>

      <p className="mb-4 text-xs text-gray-400">
        Last updated: {lastUpdated?.toLocaleTimeString()}
      </p>

      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b text-left">
            <th className="p-2">Service</th>
            <th className="p-2">Type</th>
            <th className="p-2">Message</th>
            <th className="p-2">Severity</th>
            <th className="p-2">Time</th>
          </tr>
        </thead>

        <tbody>
          {errors.map((error) => (
            <tr key={error.id} className="border-b">
              <td className="p-2">
                {error.service_name}
              </td>

              <td className="p-2">
                {error.error_type}
              </td>

              <td className="p-2">
                {error.message}
              </td>

              <td className="p-2">
                <span
                  className={`rounded px-2 py-1 text-sm ${
                    severityColor[error.severity]
                  }`}
                >
                  {error.severity}
                </span>
              </td>

              <td className="p-2">
                {new Date(error.occurred_at).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ErrorsList;