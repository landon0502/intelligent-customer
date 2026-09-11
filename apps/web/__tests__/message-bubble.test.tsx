import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { UIMessage } from "ai";
import { MessageBubble } from "@/components/chat/message-bubble";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const map: Record<string, string> = {
      thinking: "思考中...",
      toolCalling: "调用工具：{toolName}(...)",
      toolDenied: "工具调用被拒绝：{toolName}",
    };
    return (map[key] ?? key).replace(/\{(\w+)\}/g, (_, k: string) =>
      String(values?.[k] ?? "")
    );
  },
}));

const assistantWithParts = (parts: UIMessage["parts"]): UIMessage => ({
  id: "a1",
  role: "assistant",
  parts,
});

describe("MessageBubble 等待态", () => {
  it("streaming 且 parts 为空时显示加载状态", () => {
    render(<MessageBubble message={assistantWithParts([])} status="streaming" />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("streaming 且只有空白文本时不显示加载状态之外的正文", () => {
    const message = assistantWithParts([{ type: "text", text: "   " }]);
    render(<MessageBubble message={message} status="streaming" />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("streaming 且有工具调用时渲染工具状态而非加载状态", () => {
    const message = assistantWithParts([
      {
        type: "tool-knowledge_search",
        toolCallId: "t1",
        state: "output-available",
        input: {},
        output: "检索到 3 条结果",
      },
    ] as UIMessage["parts"]);
    render(<MessageBubble message={message} status="streaming" />);
    expect(screen.queryByText("思考中...")).toBeNull();
    expect(screen.getByText("检索到 3 条结果")).toBeDefined();
  });

  it("ready 时即使消息为空也不显示加载状态", () => {
    render(<MessageBubble message={assistantWithParts([])} status="ready" />);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("有文本内容时渲染正文", () => {
    const message = assistantWithParts([
      { type: "text", text: "你好，有什么可以帮你的？" },
    ]);
    render(<MessageBubble message={message} status="streaming" />);
    expect(screen.queryByText("思考中...")).toBeNull();
    expect(screen.getByText(/有什么可以帮你的/)).toBeDefined();
  });
});
