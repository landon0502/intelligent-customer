"use client";

import { useState, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const t = useTranslations("chat");
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInputText(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height =
        Math.min(Math.max(el.scrollHeight, 40), 120) + "px";
    },
    []
  );

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px";
    }
  }, [inputText, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="border-t p-4">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
          style={{ height: "40px" }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !inputText.trim()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none"
          aria-label={t("send")}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
