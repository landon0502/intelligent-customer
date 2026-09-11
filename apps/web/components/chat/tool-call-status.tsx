"use client"

import { type ReactNode } from "react"
import { useTranslations } from "next-intl"
import { getToolName } from "ai"
import type { DynamicToolUIPart, ToolUIPart } from "ai"

export interface ToolCallStatusProps {
  /** AI SDK v7 的 ToolUIPart（静态工具）或 DynamicToolUIPart（dynamic-tool） */
  toolPart: ToolUIPart | DynamicToolUIPart
}

type Tone = "pending" | "success" | "error"

const TONE_STYLES: Record<Tone, string> = {
  pending:
    "border-yellow-200 bg-yellow-50 dark:border-yellow-900/50 dark:bg-yellow-950/40",
  success:
    "border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-950/40",
  error:
    "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/40",
}

function StatusRow({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <div
      className={`mt-2 flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm text-foreground ${TONE_STYLES[tone]}`}
    >
      {children}
    </div>
  )
}

function formatResultSummary(result: unknown): string {
  const text = result == null ? "" : String(result)
  return text.length > 60 ? text.slice(0, 60) + "..." : text
}

export function ToolCallStatus({ toolPart }: ToolCallStatusProps) {
  const t = useTranslations("chat")
  const toolName = getToolName(toolPart)

  switch (toolPart.state) {
    case "input-streaming":
    case "input-available":
    case "approval-requested":
    case "approval-responded":
      return (
        <StatusRow tone="pending">
          <span className="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-yellow-500 border-t-transparent dark:border-yellow-400" />
          <span>🔧 {t("toolCalling", { toolName })}</span>
        </StatusRow>
      )

    case "output-available":
      return (
        <StatusRow tone="success">
          <span className="shrink-0 text-green-600 dark:text-green-400">
            &#10003;
          </span>
          <span>{formatResultSummary(toolPart.output)}</span>
        </StatusRow>
      )

    case "output-error":
      return (
        <StatusRow tone="error">
          <span className="shrink-0 text-red-600 dark:text-red-400">✗</span>
          <span>{toolPart.errorText}</span>
        </StatusRow>
      )

    case "output-denied":
      return (
        <StatusRow tone="error">
          <span className="shrink-0 text-red-600 dark:text-red-400">✗</span>
          <span>{t("toolDenied", { toolName })}</span>
        </StatusRow>
      )
  }
}
