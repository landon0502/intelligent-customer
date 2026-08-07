"use client"

import { useRef, useCallback } from "react"
import { useTranslations } from "next-intl"
import { Send, Square } from "lucide-react"

interface ChatInputProps {
  input: string
  setInput: (v: string) => void
  sendMessage: (msg: string) => void
  status: string
  stop: () => void
}

export function ChatInput({ input, setInput, sendMessage, status, stop }: ChatInputProps) {
  const t = useTranslations("chat")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isStreaming = status === "streaming" || status === "submitted"

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value)
      const el = e.target
      el.style.height = "auto"
      el.style.height = Math.min(Math.max(el.scrollHeight, 40), 120) + "px"
    },
    [setInput]
  )

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    sendMessage(trimmed)
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px"
    }
  }, [input, isStreaming, sendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="border-t p-4">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          disabled={isStreaming}
          rows={1}
          className="scrollbar-hide flex-1 resize-none rounded-lg border bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:opacity-50"
          style={{ height: "40px" }}
        />
        {isStreaming ? (
          <button
            onClick={stop}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-red-500 text-white hover:bg-red-600"
            aria-label={t("stop")}
          >
            <Square className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
            aria-label={t("send")}
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
