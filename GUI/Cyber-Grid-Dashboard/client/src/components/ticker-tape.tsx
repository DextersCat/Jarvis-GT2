import { motion } from "framer-motion";
import type { TickerItem } from "@/hooks/use-websocket";

interface TickerTapeProps {
  items: TickerItem[];
}

export function TickerTape({ items }: TickerTapeProps) {
  return (
    <motion.div
      className="h-10 rounded-md border border-border/40 bg-black/40 backdrop-blur px-3 flex items-center overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      data-testid="ticker-tape"
    >
      <div className="text-[10px] font-mono tracking-[0.25em] text-muted-foreground uppercase mr-3 shrink-0">
        Ticker
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="flex items-center gap-2 whitespace-nowrap">
          {items.length === 0 ? (
            <span className="text-xs font-mono text-muted-foreground/70">
              Waiting for contextual items...
            </span>
          ) : (
            items.map((item) => (
              <span
                key={`${item.short_key}-${item.label}`}
                className="text-xs font-mono px-2 py-1 rounded border border-cyan-500/30 text-cyan-300 bg-cyan-900/15"
              >
                [{item.short_key}] {item.label}
              </span>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}
