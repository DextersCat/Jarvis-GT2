import { motion } from "framer-motion";
import { FileText, Code2, Mail, Maximize2, Minimize2 } from "lucide-react";
import { useState } from "react";
import type { FocusContent } from "@/hooks/use-websocket";

interface FocusWindowProps {
  content: FocusContent | null;
}

const typeConfig = {
  docs: { icon: FileText, label: "GOOGLE DOCS", color: "rgb(59,130,246)" },
  code: { icon: Code2, label: "CODE EDITOR", color: "rgb(6,182,212)" },
  email: { icon: Mail, label: "EMAIL CLIENT", color: "rgb(168,85,247)" },
};

function SyntaxHighlight({ code }: { code: string }) {
  const lines = code.split("\n");
  return (
    <div className="font-mono text-[11px] leading-[1.7] whitespace-pre">
      {lines.map((line, i) => {
        let highlighted = line;

        highlighted = highlighted.replace(
          /(#.*$)/gm,
          '<span style="color:rgba(100,116,139,0.7)">$1</span>'
        );
        highlighted = highlighted.replace(
          /\b(import|from|class|def|async|await|if|return|print)\b/g,
          '<span style="color:rgb(168,85,247)">$1</span>'
        );
        highlighted = highlighted.replace(
          /\b(self|True|False|None)\b/g,
          '<span style="color:rgb(245,158,11)">$1</span>'
        );
        highlighted = highlighted.replace(
          /("[^"]*")/g,
          '<span style="color:rgb(52,211,153)">$1</span>'
        );
        highlighted = highlighted.replace(
          /\b(\d+\.?\d*)\b/g,
          '<span style="color:rgb(251,146,60)">$1</span>'
        );

        return (
          <div key={i} className="flex">
            <span className="select-none w-8 text-right pr-3 text-muted-foreground/30 text-[10px]">
              {i + 1}
            </span>
            <span dangerouslySetInnerHTML={{ __html: highlighted }} />
          </div>
        );
      })}
    </div>
  );
}

function renderInlineMarkdown(text: string) {
  const parts: Array<string | JSX.Element> = [];
  const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let idx = 0;

  while ((match = linkRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <a
        key={`link-${idx}`}
        href={match[2]}
        target="_blank"
        rel="noopener noreferrer"
        className="underline decoration-cyan-400/70 text-cyan-300 hover:text-cyan-200"
      >
        {match[1]}
      </a>
    );
    lastIndex = match.index + match[0].length;
    idx += 1;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function MarkdownLite({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-2 text-sm text-foreground/85 leading-relaxed">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={i} className="h-2" />;
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={i} className="text-[13px] font-semibold text-cyan-300 tracking-wide">
              {renderInlineMarkdown(trimmed.slice(4))}
            </h3>
          );
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-cyan-300 mt-[1px]">•</span>
              <span>{renderInlineMarkdown(trimmed.slice(2))}</span>
            </div>
          );
        }
        return <p key={i}>{renderInlineMarkdown(line)}</p>;
      })}
    </div>
  );
}

export function FocusWindow({ content }: FocusWindowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const resolvedContent: FocusContent = content ?? {
    type: "docs",
    title: "Waiting for input...",
    content: "Jarvis is listening. Ask a question, request a search, or just start talking.",
  };
  const config = typeConfig[resolvedContent.type];
  const Icon = config.icon;

  return (
    <motion.div
      className={`relative flex flex-col rounded-md overflow-visible ${isExpanded ? "fixed inset-4 z-50" : "h-full"}`}
      style={{
        background: "rgba(8,12,25,0.85)",
        backdropFilter: "blur(20px)",
        border: `1px solid ${config.color}15`,
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      data-testid="focus-window"
    >
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: `${config.color}15` }}
      >
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
          </div>
          <div className="w-px h-3 bg-border/30 mx-1" />
          <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
          <span className="text-[10px] font-mono tracking-[0.2em]" style={{ color: config.color }}>
            {config.label}
          </span>
          <span className="text-[10px] font-mono text-muted-foreground/40">
            / {resolvedContent.title}
          </span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 rounded-md"
          data-testid="button-expand-focus"
        >
          {isExpanded ? (
            <Minimize2 className="w-3.5 h-3.5 text-muted-foreground/50" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5 text-muted-foreground/50" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 custom-scrollbar" data-testid="focus-window-content">
        {resolvedContent.type === "code" ? (
          <SyntaxHighlight code={resolvedContent.content} />
        ) : resolvedContent.type === "email" ? (
          <div className="space-y-3">
            <MarkdownLite content={resolvedContent.content} />
          </div>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none">
            <MarkdownLite content={resolvedContent.content} />
          </div>
        )}
      </div>

      <div
        className="absolute bottom-0 left-0 right-0 h-8 pointer-events-none"
        style={{
          background: "linear-gradient(0deg, rgba(8,12,25,0.9) 0%, transparent 100%)",
        }}
      />
    </motion.div>
  );
}
