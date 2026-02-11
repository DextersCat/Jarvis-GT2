import { motion } from "framer-motion";
import { CircularGauge } from "./circular-gauge";
import type { SystemMetrics } from "@/hooks/use-websocket";

interface SystemGaugesProps {
  metrics: SystemMetrics;
}

export function SystemGauges({ metrics }: SystemGaugesProps) {
  return (
    <motion.div
      className="relative rounded-md p-3"
      style={{
        background: "rgba(10,15,30,0.6)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(148,163,184,0.06)",
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      data-testid="system-gauges"
    >
      <div className="text-[10px] font-mono tracking-[0.3em] text-muted-foreground/60 uppercase mb-3 px-1">
        System Metrics
      </div>

      <div className="grid grid-cols-2 gap-4 place-items-center">
        <CircularGauge
          label="CPU"
          value={metrics.cpu}
          maxValue={100}
          unit="%"
          color="rgb(59,130,246)"
          glowColor="rgba(59,130,246,0.4)"
          testId="gauge-cpu"
        />
        <CircularGauge
          label="Memory"
          value={metrics.memory}
          maxValue={100}
          unit="%"
          color="rgb(6,182,212)"
          glowColor="rgba(6,182,212,0.4)"
          testId="gauge-memory"
        />
        <CircularGauge
          label="GPU Temp"
          value={metrics.gpuTemp}
          maxValue={100}
          unit={"\u00B0C"}
          color="rgb(168,85,247)"
          glowColor="rgba(168,85,247,0.4)"
          testId="gauge-gpu-temp"
        />
        <CircularGauge
          label="CPU Temp"
          value={metrics.cpuTemp}
          maxValue={100}
          unit={"\u00B0C"}
          color="rgb(251,146,60)"
          glowColor="rgba(251,146,60,0.4)"
          testId="gauge-cpu-temp"
        />
        <CircularGauge
          label="NPU"
          value={metrics.npu}
          maxValue={100}
          unit="%"
          color="rgb(34,197,94)"
          glowColor="rgba(34,197,94,0.4)"
          testId="gauge-npu"
        />
        <CircularGauge
          label="GT2 -> Ollama"
          value={metrics.ollama}
          maxValue={5000}
          unit="ms"
          color="rgb(234,179,8)"
          glowColor="rgba(234,179,8,0.4)"
          testId="gauge-ollama"
        />
      </div>
    </motion.div>
  );
}
