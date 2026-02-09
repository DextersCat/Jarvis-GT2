import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Shield, Wifi, Signal } from "lucide-react";

interface HeaderProps {
  networkStatus: string;
  encryptionStatus: string;
  isConnected: boolean;
}

export function DashboardHeader({ networkStatus, encryptionStatus, isConnected }: HeaderProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (d: Date) => {
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  const formatDate = (d: Date) => {
    return d.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <header
      className="relative flex items-center justify-between px-8 py-4 border-b border-border/50"
      style={{
        background: "linear-gradient(180deg, rgba(10,15,30,0.95) 0%, rgba(5,10,20,0.85) 100%)",
        backdropFilter: "blur(20px)",
      }}
      data-testid="dashboard-header"
    >
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px]"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(59,130,246,0.5), transparent)",
          }}
        />
      </div>

      <div className="flex items-center gap-3 z-10">
        <motion.div
          className="flex items-center gap-2"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="relative">
            <Shield className="w-4 h-4 text-emerald-400" />
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ boxShadow: "0 0 8px rgba(52,211,153,0.5)" }}
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          <span className="text-xs font-mono text-emerald-400 tracking-wider" data-testid="text-encryption-status">
            {encryptionStatus}
          </span>
          <span className="text-emerald-400/40 text-xs">|</span>
          <span className="text-xs font-mono text-emerald-400/70">SECURE</span>
        </motion.div>
      </div>

      <div className="flex flex-col items-center z-10">
        <motion.div
          className="font-mono text-3xl tracking-[0.25em] text-blue-300"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          data-testid="text-current-time"
          style={{ textShadow: "0 0 20px rgba(59,130,246,0.4)" }}
        >
          {formatTime(time)}
        </motion.div>
        <span className="text-[10px] font-mono text-muted-foreground tracking-[0.3em] uppercase">
          {formatDate(time)}
        </span>
      </div>

      <div className="flex items-center gap-3 z-10">
        <motion.div
          className="flex items-center gap-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center gap-1">
            {networkStatus === "5G" ? (
              <Signal className="w-4 h-4 text-cyan-400" />
            ) : (
              <Wifi className="w-4 h-4 text-cyan-400" />
            )}
            <span className="text-xs font-mono text-cyan-400 tracking-wider" data-testid="text-network-status">
              {networkStatus}
            </span>
          </div>
          <span className="text-cyan-400/40 text-xs">|</span>
          <div className="flex items-center gap-1.5">
            <motion.div
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: isConnected ? "rgb(52,211,153)" : "rgb(239,68,68)",
                boxShadow: isConnected
                  ? "0 0 6px rgba(52,211,153,0.6)"
                  : "0 0 6px rgba(239,68,68,0.6)",
              }}
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span
              className={`text-xs font-mono tracking-wider ${isConnected ? "text-emerald-400" : "text-red-400"}`}
              data-testid="text-connection-status"
            >
              {isConnected ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
        </motion.div>
      </div>
    </header>
  );
}
