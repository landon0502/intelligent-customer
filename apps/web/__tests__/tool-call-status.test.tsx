import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ToolUIPart } from "ai";
import { ToolCallStatus } from "@/components/chat/tool-call-status";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const map: Record<string, string> = {
      toolCalling: "调用工具：{toolName}(...)",
      toolDenied: "工具调用被拒绝：{toolName}",
    };
    return (map[key] ?? key).replace(/\{(\w+)\}/g, (_, k: string) =>
      String(values?.[k] ?? "")
    );
  },
}));

/** 构造 AI SDK v7 的 ToolUIPart；状态字段由调用方指定 */
const toolPart = (
  state: string,
  extra: Record<string, unknown> = {}
): ToolUIPart =>
  ({
    type: "tool-knowledge_search",
    toolCallId: "t1",
    state,
    ...extra,
  }) as unknown as ToolUIPart;

describe("ToolCallStatus", () => {
  it.each(["input-streaming", "input-available"])(
    "%s 状态展示调用中",
    (state) => {
      render(<ToolCallStatus toolPart={toolPart(state, { input: {} })} />);
      expect(screen.getByText(/调用工具：knowledge_search/)).toBeDefined();
    }
  );

  it("output-available 状态展示工具结果", () => {
    render(
      <ToolCallStatus
        toolPart={toolPart("output-available", {
          input: {},
          output: "检索到 3 条结果",
        })}
      />
    );
    expect(screen.getByText("检索到 3 条结果")).toBeDefined();
  });

  it("结果超过 60 字符时截断", () => {
    const long = "a".repeat(80);
    render(
      <ToolCallStatus
        toolPart={toolPart("output-available", { input: {}, output: long })}
      />
    );
    expect(screen.getByText("a".repeat(60) + "...")).toBeDefined();
  });

  it("output-error 状态展示 errorText", () => {
    render(
      <ToolCallStatus
        toolPart={toolPart("output-error", { errorText: "工具执行失败" })}
      />
    );
    expect(screen.getByText("工具执行失败")).toBeDefined();
  });

  it("output-denied 状态展示被拒绝提示", () => {
    render(<ToolCallStatus toolPart={toolPart("output-denied", { input: {} })} />);
    expect(screen.getByText(/工具调用被拒绝：knowledge_search/)).toBeDefined();
  });
});
