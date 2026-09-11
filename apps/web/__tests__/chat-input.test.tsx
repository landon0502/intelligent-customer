import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { ChatInput } from "@/components/chat/chat-input";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      placeholder: "输入消息，Enter 发送，Shift+Enter 换行...",
      send: "发送",
      stop: "停止",
    };
    return map[key] ?? key;
  },
}));

interface HarnessProps {
  onSend?: (msg: string) => void;
  onStop?: () => void;
  status?: string;
  initialInput?: string;
}

/** ChatInput 是受控组件，用 Harness 提供 input/setInput 状态 */
function Harness({
  onSend = vi.fn(),
  onStop = vi.fn(),
  status = "ready",
  initialInput = "",
}: HarnessProps) {
  const [input, setInput] = useState(initialInput);
  return (
    <ChatInput
      input={input}
      setInput={setInput}
      sendMessage={onSend}
      status={status}
      stop={onStop}
    />
  );
}

const getTextarea = () =>
  screen.getByPlaceholderText(/Enter/) as HTMLTextAreaElement;

describe("ChatInput", () => {
  it("Enter 键发送消息", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    const textarea = getTextarea();
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("发送时去除首尾空白", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} initialInput="  hello  " />);
    fireEvent.keyDown(getTextarea(), { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("Shift+Enter 不发送消息（换行）", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    const textarea = getTextarea();
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("空消息不发送", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} initialInput="   " />);
    fireEvent.keyDown(getTextarea(), { key: "Enter", shiftKey: false });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("空消息时发送按钮禁用", () => {
    render(<Harness />);
    const button = screen.getByRole("button") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("有内容时发送按钮可点击并发送", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} initialInput="你好" />);
    const button = screen.getByRole("button") as HTMLButtonElement;
    expect(button.disabled).toBe(false);
    fireEvent.click(button);
    expect(onSend).toHaveBeenCalledWith("你好");
  });

  it.each(["submitted", "streaming"])(
    "status=%s 时输入框禁用，Enter 不发送",
    (status) => {
      const onSend = vi.fn();
      render(<Harness onSend={onSend} status={status} initialInput="hello" />);
      const textarea = getTextarea();
      expect(textarea.disabled).toBe(true);
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
      expect(onSend).not.toHaveBeenCalled();
    }
  );

  it.each(["submitted", "streaming"])(
    "status=%s 时展示停止按钮并触发 stop",
    (status) => {
      const onStop = vi.fn();
      render(<Harness onStop={onStop} status={status} initialInput="hello" />);
      const button = screen.getByRole("button", { name: "停止" });
      fireEvent.click(button);
      expect(onStop).toHaveBeenCalled();
    }
  );

  it("streaming 时不再展示发送按钮", () => {
    render(<Harness status="streaming" initialInput="hello" />);
    expect(screen.queryByRole("button", { name: "发送" })).toBeNull();
  });
});
