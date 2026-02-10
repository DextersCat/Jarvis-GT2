import { motion } from "framer-motion";
import { useMemo, useState } from "react";

interface MoodTrackerProps {
  onLog: (painLevel: number, anxietyLevel: number) => void;
}

interface HealthLogEntry {
  timestamp: string;
  painLevel: number;
  anxietyLevel: number;
}

const levels = ["None", "Mild", "Moderate", "Severe", "Extreme"];

const painColors = ["#1f2937", "#fb7185", "#f43f5e", "#e11d48", "#be123c"];
const anxietyColors = ["#1f2937", "#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9"];

function formatTimestamp(): string {
  const now = new Date();
  return now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function MoodTracker({ onLog }: MoodTrackerProps) {
  const [painLevel, setPainLevel] = useState(0);
  const [anxietyLevel, setAnxietyLevel] = useState(0);
  const [logs, setLogs] = useState<HealthLogEntry[]>([]);

  const recentLogs = useMemo(() => logs.slice(0, 3), [logs]);

  const handleLog = () => {
    const entry = {
      timestamp: formatTimestamp(),
      painLevel,
      anxietyLevel,
    };
    setLogs((prev) => [entry, ...prev].slice(0, 6));
    onLog(painLevel, anxietyLevel);
  };

  return (
    <motion.div
      className="relative flex flex-col rounded-md overflow-hidden"
      style={{
        background: "rgba(5,8,18,0.8)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(148,163,184,0.06)",
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      data-testid="mood-tracker"
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
        <div className="flex flex-col">
          <span className="text-[10px] font-mono tracking-[0.2em] text-rose-400/70">
            HEALTH MONITOR
          </span>
          <span className="text-[9px] font-mono text-muted-foreground/50">
            Pain & Anxiety
          </span>
        </div>
        <button
          type="button"
          onClick={handleLog}
          className="text-[9px] font-mono tracking-[0.2em] px-2 py-1 rounded-sm border"
          style={{
            borderColor: "rgba(148,163,184,0.2)",
            color: "rgba(248,113,113,0.9)",
            background: "rgba(248,113,113,0.08)",
          }}
        >
          LOG ENTRY
        </button>
      </div>

      <div className="flex-1 p-3 space-y-4">
        <div className="space-y-2">
          <div className="text-[10px] font-mono text-rose-300/70 tracking-[0.2em]">
            PAIN LEVEL
          </div>
          <div className="grid grid-cols-5 gap-2">
            {levels.map((label, index) => (
              <button
                key={`pain-${label}`}
                type="button"
                onClick={() => setPainLevel(index)}
                className="h-8 rounded-sm text-[9px] font-mono tracking-wide"
                style={{
                  color: index === painLevel ? "#fff" : "rgba(248,113,113,0.7)",
                  background:
                    index === painLevel
                      ? painColors[index]
                      : "rgba(248,113,113,0.08)",
                  border: "1px solid rgba(248,113,113,0.25)",
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-[10px] font-mono text-violet-300/70 tracking-[0.2em]">
            ANXIETY LEVEL
          </div>
          <div className="grid grid-cols-5 gap-2">
            {levels.map((label, index) => (
              <button
                key={`anxiety-${label}`}
                type="button"
                onClick={() => setAnxietyLevel(index)}
                className="h-8 rounded-sm text-[9px] font-mono tracking-wide"
                style={{
                  color: index === anxietyLevel ? "#fff" : "rgba(167,139,250,0.8)",
                  background:
                    index === anxietyLevel
                      ? anxietyColors[index]
                      : "rgba(167,139,250,0.12)",
                  border: "1px solid rgba(167,139,250,0.25)",
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-[10px] font-mono text-muted-foreground/50 tracking-[0.2em]">
            RECENT LOGS
          </div>
          <div className="space-y-1">
            {recentLogs.length === 0 ? (
              <div className="text-[10px] font-mono text-muted-foreground/40">
                No health logs yet.
              </div>
            ) : (
              recentLogs.map((entry) => (
                <div
                  key={`${entry.timestamp}-${entry.painLevel}-${entry.anxietyLevel}`}
                  className="flex items-center justify-between text-[10px] font-mono text-muted-foreground/70"
                >
                  <span>{entry.timestamp}</span>
                  <span>pain {entry.painLevel} | anxiety {entry.anxietyLevel}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
