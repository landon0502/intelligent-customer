"use client"

export interface ToolCallStatusProps {
  toolPart: {
    type: string // "tool-{toolName}"
    toolCallId: string
    toolName: string
    state: "call" | "partial-call" | "result" | "output-error"
    args?: unknown
    result?: unknown
  }
}

function formatResultSummary(result: unknown): string {
  const text = result == null ? "" : String(result)
  return text.length > 60 ? text.slice(0, 60) + "..." : text
}

export function ToolCallStatus({ toolPart }: ToolCallStatusProps) {
  const { toolName, state, result } = toolPart

  if (state === "call" || state === "partial-call") {
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3.5 py-2 text-sm">
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
        <span className="text-black">🔧 调用工具：{toolName}(...)</span>
      </div>
    )
  }

  if (state === "result") {
    const summary = formatResultSummary(result)
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3.5 py-2 text-sm">
        <span className="text-green-600">&#10003;</span>
        <span className="text-black">{summary}</span>
      </div>
    )
  }

  if (state === "output-error") {
    const errorText = result != null ? String(result) : "未知错误"
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2 text-sm">
        <span className="text-red-600">✗</span>
        <span className="text-black">{errorText}</span>
      </div>
    )
  }

  return null
}
