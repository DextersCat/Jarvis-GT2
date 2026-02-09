import { motion } from "framer-motion";
import { useMemo } from "react";

interface AIorbProps {
  mode: "speaking" | "listening" | "idle";
}

export function AIOrb({ mode }: AIorbProps) {
  const modeConfig = useMemo(() => {
    switch (mode) {
      case "speaking":
        return {
          label: "SPEAKING",
          color: "rgba(59,130,246,1)",
          glowColor: "rgba(59,130,246,0.6)",
          outerGlow: "rgba(59,130,246,0.15)",
          pulseScale: [1, 1.08, 1],
          pulseDuration: 0.8,
          waveAmplitude: 24,
          waveSpeed: 0.12,
        };
      case "listening":
        return {
          label: "LISTENING",
          color: "rgba(6,182,212,1)",
          glowColor: "rgba(6,182,212,0.5)",
          outerGlow: "rgba(6,182,212,0.12)",
          pulseScale: [1, 1.04, 1],
          pulseDuration: 1.5,
          waveAmplitude: 10,
          waveSpeed: 0.06,
        };
      default:
        return {
          label: "STANDBY",
          color: "rgba(59,130,246,0.5)",
          glowColor: "rgba(59,130,246,0.2)",
          outerGlow: "rgba(59,130,246,0.05)",
          pulseScale: [1, 1.02, 1],
          pulseDuration: 3,
          waveAmplitude: 4,
          waveSpeed: 0.03,
        };
    }
  }, [mode]);

  const waveformBars = 32;

  return (
    <div className="flex flex-col items-center gap-4" data-testid="ai-orb-container">
      <div className="relative flex items-center justify-center">
        <motion.div
          className="absolute rounded-full"
          style={{
            width: 220,
            height: 220,
            background: `radial-gradient(circle, ${modeConfig.outerGlow} 0%, transparent 70%)`,
          }}
          animate={{ scale: modeConfig.pulseScale, opacity: [0.6, 1, 0.6] }}
          transition={{ duration: modeConfig.pulseDuration * 1.5, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.div
          className="absolute rounded-full"
          style={{
            width: 180,
            height: 180,
            background: `radial-gradient(circle, ${modeConfig.outerGlow} 0%, transparent 70%)`,
          }}
          animate={{ scale: modeConfig.pulseScale }}
          transition={{ duration: modeConfig.pulseDuration, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.div
          className="relative rounded-full flex items-center justify-center"
          style={{
            width: 140,
            height: 140,
            background: `radial-gradient(circle at 35% 35%, ${modeConfig.color}, rgba(15,23,42,0.9) 80%)`,
            boxShadow: `
              0 0 30px ${modeConfig.glowColor},
              0 0 60px ${modeConfig.glowColor},
              inset 0 0 30px rgba(0,0,0,0.3)
            `,
          }}
          animate={{ scale: modeConfig.pulseScale }}
          transition={{ duration: modeConfig.pulseDuration, repeat: Infinity, ease: "easeInOut" }}
          data-testid="ai-orb"
        >
          <svg
            width="100"
            height="60"
            viewBox="0 0 100 60"
            className="absolute"
            style={{ filter: `drop-shadow(0 0 4px ${modeConfig.glowColor})` }}
          >
            {Array.from({ length: waveformBars }).map((_, i) => {
              const x = (i / waveformBars) * 100;
              const baseHeight = 4;
              return (
                <motion.rect
                  key={i}
                  x={x}
                  width={2}
                  rx={1}
                  fill={modeConfig.color}
                  opacity={0.8}
                  animate={{
                    height: [
                      baseHeight,
                      baseHeight + Math.sin(i * 0.5) * modeConfig.waveAmplitude + Math.random() * modeConfig.waveAmplitude * 0.5,
                      baseHeight,
                    ],
                    y: [
                      30 - baseHeight / 2,
                      30 - (baseHeight + Math.sin(i * 0.5) * modeConfig.waveAmplitude) / 2,
                      30 - baseHeight / 2,
                    ],
                  }}
                  transition={{
                    duration: 0.4 + Math.random() * 0.4,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * modeConfig.waveSpeed,
                  }}
                />
              );
            })}
          </svg>

          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 50%)",
            }}
          />
        </motion.div>

        <svg
          className="absolute"
          width="190"
          height="190"
          viewBox="0 0 190 190"
          style={{ filter: `drop-shadow(0 0 3px ${modeConfig.glowColor})` }}
        >
          <motion.circle
            cx="95"
            cy="95"
            r="88"
            fill="none"
            stroke={modeConfig.color}
            strokeWidth="1"
            strokeDasharray="8 6"
            opacity={0.4}
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            style={{ transformOrigin: "95px 95px" }}
          />
          <motion.circle
            cx="95"
            cy="95"
            r="92"
            fill="none"
            stroke={modeConfig.color}
            strokeWidth="0.5"
            strokeDasharray="3 12"
            opacity={0.25}
            animate={{ rotate: -360 }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
            style={{ transformOrigin: "95px 95px" }}
          />
        </svg>
      </div>

      <motion.div
        className="flex flex-col items-center gap-1"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <span className="text-xs font-mono tracking-[0.4em] uppercase" style={{ color: modeConfig.color }}>
          J.A.R.V.I.S.
        </span>
        <motion.span
          className="text-[10px] font-mono tracking-[0.3em]"
          style={{ color: modeConfig.color, opacity: 0.7 }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: modeConfig.pulseDuration, repeat: Infinity }}
          data-testid="text-ai-mode"
        >
          {modeConfig.label}
        </motion.span>
      </motion.div>
    </div>
  );
}
