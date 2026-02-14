import { motion, AnimatePresence } from "framer-motion";
import { Terminal } from "lucide-react";
import { useRef, useEffect } from "react";
import type { LogEntry } from "@/hooks/use-websocket";

interface TerminalLogProps {
  logs: LogEntry[];
}

const levelColors: Record<string, { text: string; badge: string }> = {
  info: { text: "rgb(148,163,184)", badge: "rgba(59,130,246,0.15)" },
  warn: { text: "rgb(245,158,11)", badge: "rgba(245,158,11,0.12)" },
  error: { text: "rgb(239,68,68)", badge: "rgba(239,68,68,0.12)" },
  success: { text: "rgb(52,211,153)", badge: "rgba(52,211,153,0.12)" },
  listen: { text: "rgb(56,189,248)", badge: "rgba(56,189,248,0.12)" },
  process: { text: "rgb(34,197,94)", badge: "rgba(34,197,94,0.12)" },
  speak: { text: "rgb(244,114,182)", badge: "rgba(244,114,182,0.12)" },
};

function normalizeMojibake(input: string): string {
  if (!input) return input;
  let text = input;
  try {
    // Recover common UTF-8-as-cp1252 mojibake.
    text = decodeURIComponent(escape(text));
  } catch {
    // No-op fallback below.
  }
  const replacements: Record<string, string> = {
    "ðŸ‘‚": "👂",
    "ðŸŽ¤": "🎤",
    "ðŸ“": "📝",
    "ðŸ“§": "📧",
    "ðŸ“Š": "📊",
    "ðŸ’¬": "💬",
    "âš ï¸": "⚠️",
    "âš ï¸": "⚠️",
    "âœ“": "✓",
    "âŒ": "❌",
    "â†’": "→",
  };
  for (const [bad, good] of Object.entries(replacements)) {
    text = text.split(bad).join(good);
  }
  return text;
}

export function TerminalLog({ logs }: TerminalLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <motion.div
      className="relative flex flex-col rounded-md overflow-visible"
      style={{
        background: "rgba(5,8,18,0.8)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(148,163,184,0.06)",
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      data-testid="terminal-log"
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-emerald-400/70" />
          <span className="text-[10px] font-mono tracking-[0.2em] text-emerald-400/70">
            SYSTEM LOG
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono text-muted-foreground/40">
            {logs.length} entries
          </span>
          <motion.div
            className="w-1.5 h-1.5 rounded-full bg-emerald-400"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{ boxShadow: "0 0 4px rgba(52,211,153,0.5)" }}
          />
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-3 space-y-0.5 max-h-[280px] custom-scrollbar"
        data-testid="terminal-log-content"
      >
        <AnimatePresence initial={false}>
          {logs.map((log) => {
            const levelStyle = levelColors[log.level] || levelColors.info;
            return (
              <motion.div
                key={log.id}
                className="flex items-start gap-2 py-1 px-1.5 rounded-sm font-mono text-[11px] leading-relaxed"
                style={{
                  fontFamily:
                    'Cascadia Mono, "JetBrains Mono", Consolas, "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", monospace',
                }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
              >
                <span className="text-muted-foreground/30 shrink-0 w-[52px] text-right">
                  {log.timestamp}
                </span>
                <span
                  className="shrink-0 uppercase tracking-wider px-1 rounded-sm text-[8px] leading-4 mt-px"
                  style={{
                    color: levelStyle.text,
                    background: levelStyle.badge,
                  }}
                >
                  {log.level}
                </span>
                <span style={{ color: levelStyle.text, opacity: 0.85 }}>
                  {normalizeMojibake(log.message)}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {logs.length === 0 && (
          <div className="flex items-center justify-center py-6">
            <span className="text-[10px] font-mono text-muted-foreground/30">
              Awaiting system events...
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
