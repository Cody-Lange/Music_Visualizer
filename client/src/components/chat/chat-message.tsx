import { useMemo } from "react";
import { Bot, User } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

interface Props {
  message: ChatMessageType;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Inline formatting: bold, italic, inline code, hex color swatches. */
function inlineFormat(text: string): string {
  let result = escapeHtml(text);

  // Bold: **text**
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-text-primary">$1</strong>');
  // Italic: *text*
  result = result.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, "<em>$1</em>");
  // Inline code: `text`
  result = result.replace(/`([^`]+)`/g, '<code class="rounded bg-bg-primary/60 px-1.5 py-0.5 text-xs font-mono">$1</code>');
  // Hex color swatches: #XXXXXX
  result = result.replace(
    /(#[0-9A-Fa-f]{6})\b/g,
    '<span class="inline-flex items-center gap-1"><span class="inline-block w-2.5 h-2.5 rounded-sm border border-white/10" style="background-color:$1"></span><span class="font-mono text-xs">$1</span></span>',
  );

  return result;
}

/** Minimal markdown renderer for LLM responses. */
function renderMarkdown(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  let inCodeBlock = false;

  for (const line of lines) {
    if (line.trimStart().startsWith("```")) {
      if (inCodeBlock) {
        out.push("</code></pre>");
        inCodeBlock = false;
      } else {
        out.push('<pre class="my-2 rounded-lg bg-bg-primary/60 p-3 text-xs overflow-x-auto"><code>');
        inCodeBlock = true;
      }
      continue;
    }
    if (inCodeBlock) {
      out.push(escapeHtml(line) + "\n");
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const cls =
        level <= 2
          ? "text-sm font-semibold mt-3 mb-1 text-text-primary"
          : "text-xs font-semibold mt-2 mb-0.5 text-text-secondary uppercase tracking-wide";
      out.push(`<div class="${cls}">${inlineFormat(headingMatch[2])}</div>`);
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const content = line.replace(/^\s*[-*]\s+/, "");
      out.push(
        `<div class="flex gap-2 ml-1 my-0.5"><span class="text-accent/50 shrink-0 select-none">&bull;</span><span>${inlineFormat(content)}</span></div>`,
      );
      continue;
    }

    // Numbered list
    const numMatch = line.match(/^\s*(\d+)[.)]\s+(.+)$/);
    if (numMatch) {
      out.push(
        `<div class="flex gap-2 ml-1 my-0.5"><span class="text-accent/50 shrink-0 tabular-nums select-none">${numMatch[1]}.</span><span>${inlineFormat(numMatch[2])}</span></div>`,
      );
      continue;
    }

    // Blank line
    if (line.trim() === "") {
      out.push('<div class="h-1.5"></div>');
      continue;
    }

    // Regular text
    out.push(`<div>${inlineFormat(line)}</div>`);
  }

  if (inCodeBlock) out.push("</code></pre>");
  return out.join("");
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  const formattedHtml = useMemo(() => {
    if (isUser || isSystem) return null;
    return renderMarkdown(message.content);
  }, [message.content, isUser, isSystem]);

  if (isSystem) {
    return (
      <div className="flex justify-center py-1">
        <div className="rounded-full bg-bg-tertiary/50 px-4 py-1.5 text-xs text-text-secondary/70 italic">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full mt-0.5 ${
          isUser ? "bg-accent/20" : "bg-bg-tertiary"
        }`}
      >
        {isUser ? (
          <User size={14} className="text-accent" />
        ) : (
          <Bot size={14} className="text-text-secondary" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`
          max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? "bg-accent text-white rounded-tr-sm"
            : "bg-bg-tertiary/70 text-text-primary rounded-tl-sm"
          }
        `}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
        ) : (
          <div
            className="break-words [&>div]:leading-relaxed"
            dangerouslySetInnerHTML={{ __html: formattedHtml ?? "" }}
          />
        )}
        {message.isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-accent rounded-full" />
        )}
      </div>
    </div>
  );
}
