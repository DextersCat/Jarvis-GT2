import { motion } from "framer-motion";

interface CircularGaugeProps {
  label: string;
  value: number;
  maxValue: number;
  unit: string;
  color: string;
  glowColor: string;
  testId: string;
}

export function CircularGauge({ label, value, maxValue, unit, color, glowColor, testId }: CircularGaugeProps) {
  const size = 120;
  const strokeWidth = 6;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value / maxValue, 1);
  const dashOffset = circumference * (1 - progress);

  const getStatusColor = () => {
    if (progress > 0.85) return "rgb(239,68,68)";
    if (progress > 0.65) return "rgb(245,158,11)";
    return color;
  };

  const activeColor = getStatusColor();

  return (
    <motion.div
      className="relative flex flex-col items-center gap-1.5"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      data-testid={testId}
    >
      <div className="relative">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(148,163,184,0.06)"
            strokeWidth={strokeWidth}
          />

          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={activeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1, ease: "easeOut" }}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            style={{
              filter: `drop-shadow(0 0 6px ${glowColor})`,
            }}
          />

          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius - 8}
            fill="none"
            stroke="rgba(148,163,184,0.03)"
            strokeWidth={0.5}
            strokeDasharray="2 4"
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="text-xl font-mono font-bold leading-none"
            style={{ color: activeColor, textShadow: `0 0 10px ${glowColor}` }}
            key={value}
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            data-testid={`${testId}-value`}
          >
            {Math.round(value)}
          </motion.span>
          <span className="text-[10px] font-mono text-muted-foreground/60">{unit}</span>
        </div>
      </div>

      <span className="text-[10px] font-mono tracking-[0.2em] text-muted-foreground/70 uppercase">
        {label}
      </span>
    </motion.div>
  );
}
