import { useEffect, useState } from "react";

const WS_URL = "ws://localhost:8000/ws/live";
const RETRY_MS = 2000;

export function useLiveTotal() {
  const [total, setTotal] = useState<number | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: number | undefined;
    let stopped = false;

    const connect = () => {
      if (stopped) return;

      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (stopped) return;
        setConnected(true);
        setTotal(null);
      };

      ws.onmessage = (event) => {
        try {
          const data: unknown = JSON.parse(event.data);
          if (typeof data !== "object" || data === null || !("total_errors" in data)) {
            console.error("Invalid live total message:", data);
            return;
          }

          const liveTotal = data.total_errors;
          if (liveTotal !== null && typeof liveTotal !== "number") {
            console.error("Invalid live total value:", liveTotal);
            return;
          }

          if (!stopped) setTotal(liveTotal);
        } catch (error) {
          console.error("Could not parse live total message:", error);
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        setConnected(false);
        retryTimer = window.setTimeout(connect, RETRY_MS);
      };
    };

    connect();

    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { total, connected };
}
