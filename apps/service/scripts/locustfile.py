"""智能客服系统 /api/chat/send 并发压测（Locust）

场景（默认）：
    50 个并发用户，每个用户连续发送 5 条消息（SSE 流式对话），
    用于评估系统在真实并发对话下的吞吐与延迟劣化点。

用法：
    cd apps/service
    .venv/bin/locust -f scripts/locustfile.py                  # Web 模式（http://localhost:8089）
    LT_USERS=50 .venv/bin/locust -f scripts/locustfile.py --headless -u 50 -r 10 --run-time 300s --csv scripts/loadtest_results/r50

    或直接: bash scripts/run_loadtest.sh（自动跑 50/80/100 并汇总对比）

可调环境变量：
    LT_HOST          服务地址，默认 http://127.0.0.1:8009
    LT_USERS         并发用户数，默认 50（仅在 Web 模式生效）
    LT_MSGS_PER_USER 每用户发送消息数，默认 5；设为 0 表示持续发送直到 run-time 结束
    LT_WAIT_MIN      消息间隔下限（秒），默认 0.5
    LT_WAIT_MAX      消息间隔上限（秒），默认 1.5
    LT_PASSWORD      测试用户密码，默认 test123456
    LT_QUESTION      消息内容，默认一个触发 RAG 检索的客服咨询问题
    LT_DEBUG         置 1 打印每个 SSE 事件（调试用，压测时勿开）

统计口径（重要）：
    - 内置 POST /api/chat/send 行：response_time = TTFB（Locust 在 stream=True 下
      请求头返回即计时，等于首事件耗时，不含 LLM 生成）
    - 自定义 STREAM 行：完整 SSE 流耗时（TTFB + 检索/生成 + 传输），即用户感知总延迟
    - 校验条件（在 with 块内判定，失效会正确计为失败）：HTTP 200 + 收到 finish 事件
      + 有文本输出 + 无 error 事件
"""

import json
import logging
import os
import time
import uuid

from locust import HttpUser, between, task

logger = logging.getLogger("locust.loadtest")

HOST = os.getenv("LT_HOST", "http://127.0.0.1:8009")
MSGS_PER_USER = int(os.getenv("LT_MSGS_PER_USER", "5"))
WAIT_MIN = float(os.getenv("LT_WAIT_MIN", "0.5"))
WAIT_MAX = float(os.getenv("LT_WAIT_MAX", "1.5"))
PASSWORD = os.getenv("LT_PASSWORD", "test123456")

# 用户消息内容（贴近真实客服咨询，会触发 RAG 知识库检索）
QUESTION = os.getenv(
    "LT_QUESTION",
    "你好，我是新客户，想了解下你们的产品支持哪些功能和价格区间，请简单介绍一下。",
)

# SSE 单行读取超时（秒）。响应很慢也不应无限挂起测试。
STREAM_READ_TIMEOUT = 90


class ChatLoadUser(HttpUser):
    """模拟一个登录用户在会话中连续发送消息。"""

    host = HOST
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
        # 每个 Locust 用户使用独立账号，避免并发注册碰撞
        self.username = "lt" + uuid.uuid4().hex[:10]
        self.token = self._register()
        self.conversation_id = self._create_conversation()
        self.sent = 0
        logger.debug("user %s ready, conv=%s", self.username, self.conversation_id)

    # ---------- setup（独立名称标记，不混入 /api/chat/send 指标） ----------

    def _register(self) -> str:
        resp = self.client.post(
            "/api/auth/register",
            json={"username": self.username, "password": PASSWORD},
            name="/setup:register",
        )
        if resp.status_code != 200:
            # 用户已存在等场景：退回登录
            resp = self.client.post(
                "/api/auth/login",
                json={"username": self.username, "password": PASSWORD},
                name="/setup:login",
            )
        data = resp.json()
        try:
            return data["data"]["token"]
        except (KeyError, TypeError):
            logger.warning("register/login failed: %s", resp.text[:200])
            return ""

    def _create_conversation(self) -> int:
        resp = self.client.post(
            "/api/conversations",
            json={"title": "loadtest"},
            headers={"Authorization": f"Bearer {self.token}"},
            name="/setup:create_conversation",
        )
        data = resp.json()
        try:
            return data["data"]["id"]
        except (KeyError, TypeError):
            logger.warning("create conversation failed: %s", resp.text[:200])
            return 0

    # ---------- 主任务：发送一条消息并消费完整 SSE 流 ----------

    @task
    def send_chat_message(self):
        if MSGS_PER_USER > 0 and self.sent >= MSGS_PER_USER:
            self.stop()
            return
        self.sent += 1

        payload = {
            "conversation_id": self.conversation_id,
            "id": f"lt-{self.sent}-{uuid.uuid4().hex[:6]}",
            "trigger": "submit-message",
            "messages": [
                {
                    "id": f"m-{self.sent}",
                    "role": "user",
                    "parts": [{"type": "text", "text": QUESTION}],
                }
            ],
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        t0 = time.monotonic()
        got_finish = False
        got_error = False
        has_text = False
        bytes_read = 0
        if os.getenv("LT_DEBUG"):
            print(f"[lt-debug] iter={self.sent} start conv={self.conversation_id}", flush=True)
        try:
            with self.client.post(
                "/api/chat/send",
                json=payload,
                headers=headers,
                stream=True,
                catch_response=True,
                name="/api/chat/send",
                timeout=(5, STREAM_READ_TIMEOUT),
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"HTTP {resp.status_code}")
                    return

                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    bytes_read += len(line)
                    if not line.startswith("data: "):
                        continue
                    try:
                        evt = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    etype = evt.get("type")
                    if etype == "finish":
                        got_finish = True
                    elif etype == "error":
                        got_error = True
                    elif etype == "text-start":
                        has_text = True
                    if os.getenv("LT_DEBUG"):
                        print(f"  [lt-debug] {etype} {json.dumps(evt, ensure_ascii=False)[:120]}", flush=True)

                # 判定必须在 with 块内：__exit__ 已用默认逻辑上报请求，
                # 块外再调 success/failure 无效。
                total_ms = (time.monotonic() - t0) * 1000
                if got_error:
                    resp.failure("SSE 返回 error 事件")
                elif not got_finish:
                    resp.failure("SSE 流缺少 finish 事件（连接中断）")
                elif not has_text:
                    resp.failure("SSE 流未产出任何文本")
                else:
                    resp.success()
                # 完整流耗时：仅在流正常结束时上报（作为总延迟指标）
                if got_finish:
                    self._fire_custom("STREAM", "/api/chat/send", total_ms, bytes_read)
        except Exception as e:  # noqa: BLE001 —— 网络中断/超时统一记为失败
            logger.warning("chat stream error: %s", e)
            self.environment.events.request.fire(
                request_type="POST",
                name="/api/chat/send",
                response_time=(time.monotonic() - t0) * 1000,
                response_length=bytes_read,
                exception=e,
                context={},
            )

    def _fire_custom(self, request_type: str, name: str, ms: float, length: int) -> None:
        """上报自定义指标（完整流耗时等）。"""
        try:
            self.environment.events.request.fire(
                request_type=request_type,
                name=name,
                response_time=int(ms),
                response_length=length,
                exception=None,
                context={},
            )
        except Exception:  # noqa: BLE001 —— 自定义指标失败不影响主流程
            pass
