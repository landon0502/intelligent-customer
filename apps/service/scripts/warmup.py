"""压测前预热 —— 触发 reranker/embedding 模型首次加载，排除加载时间对压测统计的污染。

用法:
    python scripts/warmup.py [--host http://127.0.0.1:8009]

行为:
    注册临时用户 → 建会话 → 发一条触发 RAG 的消息并等待流结束。
    首次执行会触发 Qwen3-Reranker 加载（数秒~数十秒）；模型已加载时很快返回。
"""

import argparse
import json
import time
import uuid

import httpx

DEFAULT_HOST = "http://127.0.0.1:8009"
RAG_QUESTION = "你好，请问企业开户需要准备哪些材料？流程是怎样的？请介绍一下。"
STREAM_TIMEOUT = httpx.Timeout(300, connect=10)


def warmup(host: str) -> None:
    client = httpx.Client(timeout=STREAM_TIMEOUT)
    username = "warm" + uuid.uuid4().hex[:8]

    resp = client.post(f"{host}/api/auth/register",
                       json={"username": username, "password": "test123456"})
    token = resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv = client.post(f"{host}/api/conversations",
                       json={"title": "warmup"}, headers=headers).json()["data"]["id"]

    t0 = time.monotonic()
    events = []
    with client.stream(
        "POST", f"{host}/api/chat/send", headers=headers,
        json={
            "conversation_id": conv,
            "id": "warm-1",
            "trigger": "submit-message",
            "messages": [{"id": "wm-1", "role": "user",
                          "parts": [{"type": "text", "text": RAG_QUESTION}]}],
        },
    ) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                evt = json.loads(line[6:])
                if evt.get("type") in ("finish", "error"):
                    events.append(evt["type"])
    elapsed = time.monotonic() - t0
    print(f"[warmup] chat status={resp.status_code} total={elapsed:.1f}s events={events}")

    if resp.status_code != 200 or "finish" not in events:
        raise SystemExit(f"[warmup] 预热请求失败: status={resp.status_code} events={events}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="压测前模型预热")
    parser.add_argument("--host", default=DEFAULT_HOST)
    args = parser.parse_args()
    warmup(args.host)
