import { motion } from "framer-motion";
import { DashboardHeader } from "@/components/dashboard-header";
import { AIOrb } from "@/components/ai-orb";
import { SidebarControls } from "@/components/sidebar-controls";
import { SystemGauges } from "@/components/system-gauges";
import { FocusWindow } from "@/components/focus-window";
import { TerminalLog } from "@/components/terminal-log";
import { MoodTracker } from "@/components/mood-tracker";
import { TickerTape } from "@/components/ticker-tape";
import { useWebSocket } from "@/hooks/use-websocket";
import { useCallback } from "react";

export default function Dashboard() {
  const { data, sendCommand } = useWebSocket();

  const handleToggle = useCallback(
    (key: string, value: boolean) => {
      sendCommand("toggle", { key, value });
    },
    [sendCommand]
  );

  const handleHealthLog = useCallback(
    (painLevel: number, anxietyLevel: number) => {
      sendCommand("health_update", { type: "pain", level: painLevel });
      sendCommand("health_update", { type: "anxiety", level: anxietyLevel });
    },
    [sendCommand]
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden relative" data-testid="dashboard-root">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: `
            radial-gradient(ellipse at 20% 50%, rgba(59,130,246,0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(6,182,212,0.04) 0%, transparent 40%),
            radial-gradient(ellipse at 50% 80%, rgba(168,85,247,0.03) 0%, transparent 40%)
          `,
        }}
      />

      <div className="relative z-10 flex flex-col h-full">
        <DashboardHeader
          networkStatus={data.networkStatus}
          encryptionStatus={data.encryptionStatus}
          isConnected={data.isConnected}
        />

        <div className="flex-1 flex overflow-hidden">
          <motion.aside
            className="w-[300px] shrink-0 flex flex-col gap-5 p-4 border-r border-border/30 overflow-y-auto custom-scrollbar"
            style={{
              background: "rgba(8,12,25,0.5)",
              backdropFilter: "blur(16px)",
            }}
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            data-testid="sidebar-panel"
          >
            <div className="flex flex-col items-center py-6">
              <AIOrb mode={data.jarvisState.mode} />
            </div>

            <SidebarControls
              gamingMode={data.jarvisState.gamingMode}
              muteMic={data.jarvisState.muteMic}
              conversationalMode={data.jarvisState.conversationalMode}
              onToggle={handleToggle}
            />

            <SystemGauges metrics={data.metrics} />
          </motion.aside>

          <main className="flex-1 flex flex-col gap-4 p-4 overflow-hidden">
            <div className="flex-1 min-h-0">
              <FocusWindow content={data.focusContent} />
            </div>

            <div className="h-[320px] shrink-0 flex flex-col xl:flex-row gap-4">
              <div className="flex-1 min-w-0">
                <TerminalLog logs={data.logs} />
              </div>
              <div className="w-full xl:w-[320px]">
                <MoodTracker onLog={handleHealthLog} />
              </div>
            </div>

            <div className="h-10 shrink-0">
              <TickerTape items={data.tickerItems} />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
