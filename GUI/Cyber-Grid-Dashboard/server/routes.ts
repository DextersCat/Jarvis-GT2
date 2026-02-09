import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { log } from "./index";

interface SystemMetrics {
  cpu: number;
  memory: number;
  gpuTemp: number;
  cpuTemp: number;
}

interface JarvisState {
  mode: "speaking" | "listening" | "idle";
  gamingMode: boolean;
  muteMic: boolean;
  conversationalMode: boolean;
}



export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  const wss = new WebSocketServer({ server: httpServer, path: "/ws" });

  // Real state and data from Jarvis
  let metrics: SystemMetrics = { cpu: 0, memory: 0, gpuTemp: 0, cpuTemp: 0 };
  let state: JarvisState = {
    mode: "idle",
    gamingMode: false,
    muteMic: false,
    conversationalMode: true,
  };

  let logs: Array<{ id: string; timestamp: string; level: string; message: string }> = [];
  const maxLogs = 50;  // Keep last 50 logs

  let currentFocus: any = null;  // Will receive real focus content from Jarvis

  wss.on("connection", (ws) => {
    // Send initial state to new client
    ws.send(
      JSON.stringify({
        type: "full",
        data: {
          metrics,
          jarvisState: state,
          logs: logs.slice(-8),  // Last 8 real logs
          focusContent: currentFocus,
          networkStatus: "Connected",
          encryptionStatus: "AES-256",
        },
      })
    );

    // Handle messages from Jarvis
    ws.on("message", (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        
        // Real data from Jarvis dashboard bridge
        if (msg.type === "metrics" && msg.data) {
          metrics = msg.data;
          broadcast(wss, msg, ws);
        } else if (msg.type === "state" && msg.data) {
          state = { ...state, ...msg.data };
          broadcast(wss, msg, ws);
        } else if (msg.type === "log" && msg.data) {
          logs.push(msg.data);
          if (logs.length > maxLogs) logs.shift();
          broadcast(wss, msg, ws);
        } else if (msg.type === "focus" && msg.data) {
          currentFocus = msg.data;
          broadcast(wss, msg, ws);
        } else if (msg.command === "toggle" && msg.key) {
          // Handle UI control toggles
          const key = msg.key as keyof JarvisState;
          if (key in state && key !== "mode") {
            (state as any)[key] = msg.value;
            broadcast(wss, { type: "state", data: state }, ws);
          }
        }
      } catch (e) {
        console.error(`Message parse error: ${e}`);
      }
    });
  });

  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  return httpServer;
}

function broadcast(wss: WebSocketServer, data: any, excludeClient?: WebSocket) {
  const payload = JSON.stringify(data);
  wss.clients.forEach((client) => {
    // Skip the sender to avoid echoing back
    if (client !== excludeClient && client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  });
}
