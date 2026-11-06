import { useEffect, useState } from "react";
import useAutoRefresh from "../hooks/useAutoRefresh";
import AsyncSection from "./AsyncSection";

type Correlation = {
  root_cause: {
    service_name: string;
    started_at: string;
    top_error: string | null;
  } | null;
  affected: {
    service_name: string;
    lag_seconds: number;
    top_error: string | null;
  }[];
};

function toDate(value: string) {
  return new Date(value);
}

function formatDuration(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds} seconds`;
}

function RootCauseCard() {
  const [now, setNow] = useState(0);
  const { data, loading, error } = useAutoRefresh<Correlation>(
    async () => {
      const response = await fetch("http://localhost:8000/incident-correlation");
      if (!response.ok) {
        throw new Error(
          `Incident correlation request failed with status ${response.status}`
        );
      }
      return response.json();
    },
    5000
  );
  const stories = data?.root_cause ? [data] : [];

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="p-6">
      <h2 className="mb-4 text-2xl font-bold">Root Cause (andaaza)</h2>
      <AsyncSection
        loading={loading}
        error={error}
        isEmpty={stories.length === 0}
        emptyMessage="Koi correlated incident nahi: sab theek hai, ya sirf ek service mein dikkat hai."
      >
        {stories.map((story) => {
          const root = story.root_cause!;
          return (
            <div
              key={root.service_name}
              className="rounded border border-red-200 bg-red-50 p-4"
            >
              <p className="text-xs font-semibold uppercase text-red-600">
                Probable root cause
              </p>
              <p className="text-2xl font-bold">{root.service_name}</p>
              <p className="text-sm text-gray-700">{root.top_error ?? "-"}</p>
              <p className="mt-1 text-xs text-gray-500">
                Shuru hua {toDate(root.started_at).toLocaleTimeString()} (
                {formatDuration(now - toDate(root.started_at).getTime())} se)
              </p>

              <p className="mt-4 text-xs font-semibold uppercase text-gray-500">
                Iske baad toote
              </p>
              <ul className="text-sm">
                {story.affected.map((affected) => (
                  <li
                    key={affected.service_name}
                    className="flex items-baseline justify-between gap-4 border-t border-red-100 py-1"
                  >
                    <span className="font-medium">{affected.service_name}</span>
                    <span className="text-gray-600">+{affected.lag_seconds}s</span>
                    <span className="text-gray-700">
                      {affected.top_error ?? "-"}
                    </span>
                  </li>
                ))}
              </ul>

              <p className="mt-3 text-xs text-gray-500">
                Andaaza hai (pehle toota = shayad wajah), pakka nahi.
              </p>
            </div>
          );
        })}
      </AsyncSection>
    </section>
  );
}

export default RootCauseCard;
