"""UIMessage[] → LangChain Message 列表转换器。

将 AI SDK 前端发送的 UIMessage 格式转换为 LangChain 的
HumanMessage / AIMessage / ToolMessage 列表，供 Agent 消费。
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage


def _extract_tool_name(part: dict) -> str:
    """从 part 中提取工具名称。

    支持两种格式：
    - Legacy: type="tool-invocation"，名称在 toolName 字段
    - 动态: type="tool-{toolName}"，名称从 type 字段提取
    """
    name = part.get("toolName", part.get("name", ""))
    if name:
        return name
    # 动态格式: 从 type="tool-{toolName}" 中提取
    part_type = part.get("type", "")
    if part_type.startswith("tool-") and part_type != "tool-invocation":
        return part_type[len("tool-"):]
    return ""


def _extract_tool_call_id(part: dict) -> str:
    """从 part 中提取工具调用 ID。"""
    return part.get("toolCallId", part.get("tool_invocation_id", ""))


def _extract_tool_args(part: dict) -> dict:
    """从 part 中提取工具参数。

    优先取 AI SDK 7.x 的 input 字段，回退到旧版 args 字段。
    """
    return part.get("input", part.get("args", {}))


def ui_messages_to_langchain(ui_messages: list[dict]) -> list[BaseMessage]:
    """将 AI SDK UIMessage[] 转换为 LangChain Message 列表。

    Args:
        ui_messages: AI SDK UIMessage 格式的消息列表，每条消息包含
            role 和 parts 字段。

    Returns:
        LangChain BaseMessage 列表，可能包含 HumanMessage、AIMessage
        和 ToolMessage。
    """
    result: list[BaseMessage] = []

    for msg in ui_messages:
        if msg["role"] == "user":
            text = "".join(
                p.get("text", "")
                for p in msg.get("parts", [])
                if p.get("type") == "text"
            )
            if text:
                result.append(HumanMessage(content=text))

        elif msg["role"] == "assistant":
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[dict] = []

            for p in msg.get("parts", []):
                part_type = p.get("type", "")

                if part_type == "text":
                    text_parts.append(p.get("text", ""))

                elif part_type == "tool-invocation":
                    # Legacy 格式: type="tool-invocation"
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available", "output-error"):
                        tool_results.append(p)

                elif part_type.startswith("tool-"):
                    # 动态格式: type="tool-{toolName}"
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available", "output-error"):
                        tool_results.append(p)

            # 创建 AIMessage（含文本和工具调用）
            if text_parts or tool_calls:
                tc_list = [
                    {
                        "name": _extract_tool_name(tc),
                        "args": _extract_tool_args(tc),
                        "id": _extract_tool_call_id(tc),
                        "type": "tool_call",
                    }
                    for tc in tool_calls
                ]
                kwargs: dict = {"content": " ".join(text_parts) if text_parts else ""}
                if tc_list:
                    kwargs["tool_calls"] = tc_list
                result.append(AIMessage(**kwargs))

            # 创建 ToolMessage（工具结果）
            for tr in tool_results:
                # 优先取 AI SDK 7.x 的 output 字段，回退到旧版 result 字段
                content = tr.get("output", tr.get("result", ""))
                # output-error state: 使用 errorText 作为 content
                if tr.get("state") == "output-error":
                    content = tr.get("errorText", str(content))
                result.append(
                    ToolMessage(
                        content=str(content),
                        tool_call_id=_extract_tool_call_id(tr),
                        name=_extract_tool_name(tr),
                    )
                )

    return result
