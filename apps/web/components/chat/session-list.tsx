"use client";

import { useTranslations } from "next-intl";
import { Plus, X } from "lucide-react";
import type { Session } from "@/config/mock-chat";

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onNew,
  onDelete,
}: SessionListProps) {
  const t = useTranslations("chat");

  return (
    <div className="w-64 bg-background border-r flex flex-col">
      <div className="p-3 border-b flex items-center justify-between">
        <h2 className="text-sm font-medium">{t("sessionList")}</h2>
        <button
          onClick={onNew}
          className="inline-flex items-center gap-1 text-xs text-primary border border-dashed border-primary rounded-md px-2 py-1 hover:bg-primary/5"
        >
          <Plus className="h-3 w-3" />
          {t("newSession")}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => onSelect(session.id)}
            className={`group px-3 py-2.5 cursor-pointer border-b last:border-b-0 ${
              session.id === currentSessionId
                ? "bg-primary/5 border-l-2 border-l-primary"
                : "hover:bg-muted/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm truncate flex-1">{session.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground p-0.5"
                aria-label="Delete session"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <span className="text-xs text-muted-foreground">{session.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
