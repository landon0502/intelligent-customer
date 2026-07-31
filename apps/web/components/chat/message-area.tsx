"use client"

import { useRef, useEffect } from "react"
import { useTranslations } from "next-intl"
import type { DisplayMessage } from "./session-list"
import { MessageBubble } from "./message-bubble"

interface MessageAreaProps {
  messages: DisplayMessage[]
}

export function MessageArea({ messages }: MessageAreaProps) {
  const t = useTranslations("chat")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">{t("emptySession")}</p>
      </div>
    )
  }

  return (
    <div className="relative flex-1">
      <div className="absolute top-0 right-0 bottom-0 left-0 overflow-y-auto p-5">
        <div className="space-y-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
