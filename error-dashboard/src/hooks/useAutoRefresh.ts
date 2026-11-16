import { useEffect, useRef, useState } from 'react';

function useAutoRefresh<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 5000,
  enabled: boolean = true
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFnRef = useRef(fetchFn);

  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  useEffect(() => {
    if (!enabled) return;

    let isMounted = true;

    const load = async () => {
      try {
        const result = await fetchFnRef.current();

        if (isMounted) {
          setData(result);
          setError(null);
        }
      } catch {
        if (isMounted) {
          setError('Unable to load data. Please check if the backend is running.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    load();

    const interval = setInterval(load, intervalMs);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [intervalMs, enabled]);

  return { data, loading, error };
}

export default useAutoRefresh;