"use client"

import { useTranslations } from "next-intl"
import { Plus, X } from "lucide-react"
import type { ToolCall } from "./tool-call-status"

export interface DisplaySession {
  id: number
  title: string
  time: string
}

export interface DisplayMessage {
  id: string
  role: "user" | "assistant"
  content: string
  time: string
  toolCalls?: ToolCall[]
}

interface SessionListProps {
  sessions: DisplaySession[]
  currentSessionId: number | null
  onSelect: (id: number) => void
  onNew: () => void
  onDelete: (id: number) => void
}

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onNew,
  onDelete,
}: SessionListProps) {
  const t = useTranslations("chat")

  return (
    <div className="flex w-64 flex-col border-r bg-background">
      <div className="flex items-center justify-between border-b p-3">
        <h2 className="text-sm font-medium">{t("sessionList")}</h2>
        <button
          onClick={onNew}
          className="inline-flex items-center gap-1 rounded-md border border-dashed border-primary px-2 py-1 text-xs text-primary hover:bg-primary/5"
        >
          <Plus className="h-3 w-3" />
          {t("newSession")}
        </button>
      </div>
      <div className="relative flex-1 overflow-hidden">
        <div className="absolute top-0 right-0 bottom-0 left-0 overflow-y-auto">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onSelect(session.id)}
              className={`group cursor-pointer border-b px-3 py-2.5 last:border-b-0 ${
                session.id === currentSessionId
                  ? "border-l-2 border-l-primary bg-primary/5"
                  : "hover:bg-muted/50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="flex-1 truncate text-sm">{session.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(session.id)
                  }}
                  className="p-0.5 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-foreground"
                  aria-label="Delete session"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              <span className="text-xs text-muted-foreground">
                {session.time}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
