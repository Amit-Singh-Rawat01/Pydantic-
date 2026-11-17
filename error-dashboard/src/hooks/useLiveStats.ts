import { useEffect, useState } from "react";

const WS_URL = "ws://localhost:8000/ws/live";
const STALE_AFTER_MS = 3000;

export function useLiveStats<T>() {
  const [stats, setStats] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const [silentFor, setSilentFor] = useState(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: number | undefined;
    let stopped = false;
    let lastMessageAt = Date.now();

    const connect = () => {
      if (stopped) return;

      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (stopped) return;
        lastMessageAt = Date.now();
        setConnected(true);
      };

      ws.onmessage = (event) => {
        if (stopped) return;
        lastMessageAt = Date.now();
        setSilentFor(0);
        try {
          const nextStats = JSON.parse(event.data) as T;
          setStats(nextStats);
        } catch (error) {
          console.error("Could not parse live stats message:", error);
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        setConnected(false);
        setSilentFor(0);
        setStats(null);
        retryTimer = window.setTimeout(connect, 2000);
      };
    };

    const watchman = window.setInterval(() => {
      if (ws?.readyState !== WebSocket.OPEN) {
        setSilentFor(0);
        return;
      }

      const gap = Date.now() - lastMessageAt;
      setSilentFor(gap > STALE_AFTER_MS ? Math.round(gap / 1000) : 0);
    }, 1000);

    connect();

    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      window.clearInterval(watchman);
      ws?.close();
    };
  }, []);

  return { stats, connected, silentFor };
}
