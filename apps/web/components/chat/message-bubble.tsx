"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/config/mock-chat";
import { ToolCallStatus } from "./tool-call-status";

const markdownComponents = {
  table: ({ children }: { children?: React.ReactNode }) => (
    <table className="border-collapse text-sm my-2 w-full">{children}</table>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border px-2 py-1 bg-muted text-left">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border px-2 py-1">{children}</td>
  ),
  code: ({
    children,
    className,
  }: {
    children?: React.ReactNode;
    className?: string;
  }) => (
    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{children}</code>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-3 border-muted-foreground/30 pl-3 text-muted-foreground my-2">
      {children}
    </blockquote>
  ),
};

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-primary-foreground rounded-xl rounded-br-sm max-w-[70%] px-3.5 py-2.5">
          {message.content.split("\n").map((line, i) => (
            <React.Fragment key={i}>
              {i > 0 && <br />}
              {line}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="bg-background border rounded-xl rounded-bl-sm max-w-[70%] px-3.5 py-2.5">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {message.content}
        </ReactMarkdown>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallStatus toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
}
