import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import type { UIMessage } from "ai";
import { MessageArea } from "@/components/chat/message-area";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      emptySession: "选择或创建一个会话开始对话",
      thinking: "思考中...",
    };
    return map[key] ?? key;
  },
}));

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const userMessage: UIMessage = {
  id: "u1",
  role: "user",
  parts: [{ type: "text", text: "你好" }],
};

const emptyAssistantMessage: UIMessage = {
  id: "a1",
  role: "assistant",
  parts: [],
};

const textAssistantMessage: UIMessage = {
  id: "a2",
  role: "assistant",
  parts: [{ type: "text", text: "你好，有什么可以帮你的？" }],
};

describe("MessageArea 加载状态", () => {
  it("submitted（已发送、等待响应）时显示加载状态", () => {
    render(<MessageArea messages={[userMessage]} status="submitted" />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("等待响应期间用户消息仍然可见", () => {
    render(<MessageArea messages={[userMessage]} status="submitted" />);
    expect(screen.getByText("你好")).toBeDefined();
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });

  it("streaming 但 assistant 尚无内容时显示加载状态", () => {
    render(
      <MessageArea
        messages={[userMessage, emptyAssistantMessage]}
        status="streaming"
      />
    );
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("assistant 开始输出文本后隐藏加载状态", () => {
    render(
      <MessageArea
        messages={[userMessage, textAssistantMessage]}
        status="streaming"
      />
    );
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("ready 状态不显示加载状态", () => {
    render(
      <MessageArea
        messages={[userMessage, textAssistantMessage]}
        status="ready"
      />
    );
    expect(screen.queryByRole("status")).toBeNull();
  });
});
