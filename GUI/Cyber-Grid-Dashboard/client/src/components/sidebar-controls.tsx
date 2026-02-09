import { motion } from "framer-motion";
import { Gamepad2, MicOff, MessageCircle } from "lucide-react";
import { Switch } from "@/components/ui/switch";

interface SidebarControlsProps {
  gamingMode: boolean;
  muteMic: boolean;
  conversationalMode: boolean;
  onToggle: (key: string, value: boolean) => void;
}

interface ControlItemProps {
  icon: typeof Gamepad2;
  label: string;
  sublabel: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  color: string;
  delay: number;
  testId: string;
}

function ControlItem({ icon: Icon, label, sublabel, checked, onCheckedChange, color, delay, testId }: ControlItemProps) {
  return (
    <motion.div
      className="relative rounded-md p-4 flex flex-col gap-3"
      style={{
        background: "rgba(15,23,42,0.5)",
        backdropFilter: "blur(16px)",
        border: `1px solid ${checked ? color + "40" : "rgba(148,163,184,0.08)"}`,
      }}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      {checked && (
        <motion.div
          className="absolute inset-0 rounded-md pointer-events-none"
          style={{
            background: `radial-gradient(ellipse at center, ${color}08 0%, transparent 70%)`,
            boxShadow: `inset 0 0 20px ${color}06`,
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        />
      )}

      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{
              background: checked ? `${color}18` : "rgba(148,163,184,0.06)",
              border: `1px solid ${checked ? color + "30" : "rgba(148,163,184,0.08)"}`,
            }}
          >
            <Icon
              className="w-3.5 h-3.5"
              style={{ color: checked ? color : "rgba(148,163,184,0.5)" }}
            />
          </div>
          <div className="flex flex-col">
            <span
              className="text-xs font-mono tracking-wider"
              style={{ color: checked ? color : "rgba(148,163,184,0.7)" }}
            >
              {label}
            </span>
            <span className="text-[9px] font-mono text-muted-foreground/50 tracking-wide">
              {sublabel}
            </span>
          </div>
        </div>
        <Switch
          checked={checked}
          onCheckedChange={onCheckedChange}
          data-testid={testId}
        />
      </div>
    </motion.div>
  );
}

export function SidebarControls({ gamingMode, muteMic, conversationalMode, onToggle }: SidebarControlsProps) {
  return (
    <div className="flex flex-col gap-2" data-testid="sidebar-controls">
      <motion.div
        className="text-[10px] font-mono tracking-[0.3em] text-muted-foreground/60 uppercase px-1 mb-1"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        System Controls
      </motion.div>

      <ControlItem
        icon={Gamepad2}
        label="GAMING MODE"
        sublabel="Low latency priority"
        checked={gamingMode}
        onCheckedChange={(v) => onToggle("gamingMode", v)}
        color="rgb(168,85,247)"
        delay={0.3}
        testId="switch-gaming-mode"
      />

      <ControlItem
        icon={MicOff}
        label="MUTE MIC"
        sublabel="Microphone disabled"
        checked={muteMic}
        onCheckedChange={(v) => onToggle("muteMic", v)}
        color="rgb(239,68,68)"
        delay={0.4}
        testId="switch-mute-mic"
      />

      <ControlItem
        icon={MessageCircle}
        label="CONV. MODE"
        sublabel="Natural dialogue"
        checked={conversationalMode}
        onCheckedChange={(v) => onToggle("conversationalMode", v)}
        color="rgb(6,182,212)"
        delay={0.5}
        testId="switch-conversational-mode"
      />
    </div>
  );
}
