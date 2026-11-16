import { useEffect, useState } from "react";

const WS_URL = "ws://localhost:8000/ws/live";

export function useLiveStats<T>() {
  const [stats, setStats] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: number | undefined;
    let stopped = false;

    const connect = () => {
      if (stopped) return;

      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (!stopped) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const nextStats = JSON.parse(event.data) as T;
          if (!stopped) setStats(nextStats);
        } catch (error) {
          console.error("Could not parse live stats message:", error);
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        setConnected(false);
        setStats(null);
        retryTimer = window.setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { stats, connected };
}
