import { useState, useEffect, useCallback, useRef } from "react";

export interface SystemMetrics {
  cpu: number;
  memory: number;
  gpuTemp: number;
  cpuTemp: number;
  npu: number;
  ollama: number;
}

export interface JarvisState {
  mode: "speaking" | "listening" | "idle";
  gamingMode: boolean;
  muteMic: boolean;
  conversationalMode: boolean;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "info" | "warn" | "error" | "success" | "listen" | "process" | "speak";
  message: string;
}

export interface FocusContent {
  type: "docs" | "code" | "email";
  title: string;
  content: string;
}

export interface TickerItem {
  short_key: string;
  label: string;
}

export interface DashboardData {
  metrics: SystemMetrics;
  jarvisState: JarvisState;
  logs: LogEntry[];
  focusContent: FocusContent;
  tickerItems: TickerItem[];
  networkStatus: "5G" | "4G" | "3G" | "disconnected";
  encryptionStatus: "AES-256" | "AES-128" | "none";
  isConnected: boolean;
}

const initialData: DashboardData = {
  metrics: { cpu: 0, memory: 0, gpuTemp: 0, cpuTemp: 0, npu: 0, ollama: 0 },
  jarvisState: {
    mode: "idle",
    gamingMode: false,
    muteMic: false,
    conversationalMode: false,
  },
  logs: [],
  focusContent: {
    type: "docs",
    title: "Waiting for input...",
    content: "Jarvis is listening. Ask a question, request a search, or just start talking.",
  },
  tickerItems: [],
  networkStatus: "5G",
  encryptionStatus: "AES-256",
  isConnected: false,
};

export function useWebSocket() {
  const [data, setData] = useState<DashboardData>(initialData);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setData((prev) => ({ ...prev, isConnected: true }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "metrics") {
            setData((prev) => ({ ...prev, metrics: message.data }));
          } else if (message.type === "state") {
            setData((prev) => ({ ...prev, jarvisState: message.data }));
          } else if (message.type === "log") {
            setData((prev) => ({
              ...prev,
              logs: [...prev.logs.slice(-49), message.data],
            }));
          } else if (message.type === "focus") {
            setData((prev) => ({ ...prev, focusContent: message.data }));
          } else if (message.type === "ticker") {
            setData((prev) => ({ ...prev, tickerItems: message.data || [] }));
          } else if (message.type === "full") {
            setData((prev) => ({ ...prev, ...message.data, isConnected: true }));
          }
        } catch {}
      };

      ws.onclose = () => {
        setData((prev) => ({ ...prev, isConnected: false }));
        reconnectTimerRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimerRef.current = setTimeout(connect, 3000);
    }
  }, []);

  const sendCommand = useCallback(
    (command: string, payload?: Record<string, unknown>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ command, ...payload }));
      }
    },
    []
  );

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, sendCommand };
}
