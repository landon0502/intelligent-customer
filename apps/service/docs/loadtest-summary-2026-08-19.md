# 智能客服系统并发压测总结

- 日期：2026-08-19
- 测试工具：[Locust 2.46.3](../scripts/locustfile.py)
- 压测脚本：`apps/service/scripts/locustfile.py`、`apps/service/scripts/run_loadtest.sh`、`apps/service/scripts/warmup.py`
- 测试对象：`POST /api/chat/send`（SSE 流式对话，含 RAG 检索 + DeepSeek 生成）

---

## 1. 测试场景

- **并发用户数从 10 到 50 逐档实测系统容量**（10 / 20 / 30 / 50），每用户连续发送 5 条消息（触发 RAG 检索）
- 每用户独立注册 + 建会话（贴近真实登录场景）
- **预热机制**：每档压测前先发一条 RAG 消息触发 reranker/embedding 模型加载（`warmup.py`），**统计窗口排除模型首次加载时间**
- 指标口径：
  - **总耗时（STREAM）**：从发起到收到 `finish` 事件的完整流耗时（用户感知延迟）
  - **TTFB**：Locust 对 stream 请求的计时（含服务端排队，非纯网络首字节）

## 2. 环境

| 项 | 值 |
| --- | --- |
| 服务 | 单进程 uvicorn，`uv run python main.py`，端口 8009 |
| LLM | DeepSeek API（`deepseek-v4-flash`，远程） |
| Embedding | 本地 BAAI/bge-base-zh-v1.5（**CPU**，`EMBEDDING_DEVICE=cpu`） |
| Reranker | 本地 Qwen3-Reranker-0.6B（MPS，**批处理**，`rerank.enabled=true`） |
| 向量库 | Chroma（localhost:8000） |
| 数据库 | MySQL，SQLAlchemy async 连接池（20+30=50） |
| 机器 | macOS（MPS 推理），内存 16G（压测期间仅 ~120-200M 空闲，compressor 峰值 8.4G） |

## 3. 测试过程（多轮）

### 3.1 首轮（期间 DeepSeek 欠费）——数据污染，仅作参考

| 并发 | 请求 | 成功 | 失败 | 失败主因 |
| --- | --- | --- | --- | --- |
| 50 | 205 | 52 (25%) | 153 | 105× SSE error（AI 服务不可用）+ 38× HTTP 500 |
| 80 | 400 | 0 | 400 | 400× SSE error |

> 用户反馈 DeepSeek 欠费导致 SSE error，充值后重跑。

### 3.2 修复前基线（欠费已解决，池 15=默认 5+10，300s/档）

| 并发 | 请求 | 成功流 | 成功率 | 成功流均耗 | 成功流 p90 | 成功吞吐 |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | 185 | 101 | **55%** | 50.6s | 67s | 0.34 条/s |
| 80 | 259 | 102 | **39%** | 49.4s | 86s | 0.34 条/s |
| 100 | 310 | 115 | **37%** | 42.8s | 52s | 0.38 条/s |

**结论**：成功率随并发下降（55%→37%），成功吞吐锁死在 ~0.35 条/s —— 系统有硬性并发上限。

**失败根因（服务日志实锤）**：
1. **DB 连接池被打爆**：`QueuePool limit of size 5 overflow 10 reached, timeout 30` ——
   - `create_async_engine` 未传配置里的 `DB_POOL_SIZE=10/DB_MAX_OVERFLOW=20`，实际用默认 5+10=15
   - SSE 流**全程持有 DB session**（依赖注入跨流生命周期 40-50s），50 并发流瞬间占满 15 连接
2. **MPS 本地推理串行**：Qwen3-Reranker 重排并发下每次 4.5-8s（预热后 0.34s），加深排队

### 3.3 修复后逐轮验证（50 并发）

| 版本 | 配置 | 成功率 | 成功流均耗 | 关键变化 |
| --- | --- | --- | --- | --- |
| 修复前 | 池 15 | 55% | 50.6s | 基线 |
| ① 池 15→30 + chat 流不持 session | 30 | **2%** | 141.9s | 池仍不够 + 新暴露 reranker 并发 bug |
| ② + reranker 加载/推理加锁 | 30 | **48%** | 69.1s | `meta tensor` 崩溃消除 |
| ③ 池 30→50（.env 20+30） | 50 | **96%** | 67.5s | DB 超时归零 |
| ④ + reranker 批处理 + embedding→CPU | 50 | **95%** | 68.9s | 隔离验证批处理 6.4s，但被机器资源拖慢 |

### 3.4 深度定位（批处理后 50 并发仍 ~65s 的原因）

隔离测试证明**批处理代码有效**（20 并发 rerank 从 ~40s 串行降到 6.4s），但进入 50 并发完整负载后：
- rerank 服务内均值回到 **33.9s**（MPS 被系统拖慢）
- Chroma（含 embedding）均值 **9.68s**
- **系统内存极紧张**：`PhysMem 15G used / 仅 120-160M unused / compressor 峰值 8.4G`，CPU 40% 花在内存压缩

**结论：瓶颈从「reranker 串行排队」转移到「机器物理资源（内存）不足」**。批处理、embedding 移 CPU 等代码优化方向正确，但 16G 内存无法承载 50 并发 RAG 对话的本地推理负载。

## 4. 最终容量实测（修复后 + 预热，300s/档）

| 并发 | 请求 | 成功率 | avg | p50 | p90 | p99 | 成功吞吐 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **10** | 50 | **100%** | 14.8s | **13s** | 23s | 35s | 0.17 条/s |
| **20** | 100 | **100%** | 27.0s | **25s** | 38s | 94s | 0.33 条/s |
| **30** | 150 | **100%** | 39.5s | **38s** | 49s | 83s | **0.50 条/s** |
| **50** | 142 | **95%** | 68.9s | **65s** | 100s | 102s | 0.45 条/s |

**容量曲线**：

- **10 并发**：甜点区（p50 13s）
- **20 并发**：最佳工作点（p50 25s，100% 成功）
- **30 并发**：稳定上限（p50 38s，仍 100% 成功，延迟明显走高）
- **50 并发**：过载（p50 65s，内存打爆 + 5% 失败）

延迟随并发**非线性上升**（20→50，p50 25s→65s），成功吞吐峰值在 ~30 并发（0.50 条/s），50 并发反降——确凿证明**机器资源容量是最终瓶颈**。

## 5. 修复与优化清单（最终状态）

| 文件 | 改动 | 效果 |
| --- | --- | --- |
| `database/mysql.py` | `create_async_engine` 显式传 `pool_size/max_overflow/pool_pre_ping` | 消除 DB 500 |
| `.env` | `DB_POOL_SIZE=20, DB_MAX_OVERFLOW=30`（池 50） | DB 超时归零 |
| `api/chat.py` | SSE 流式期间不再持有 DB session（短生命周期 session） | 连接不泄漏 |
| `models/reranker.py` | 加载锁（防并发加载 meta tensor 崩溃）+ **批处理**（合并并发请求统一 predict，单 worker 串行推理） | 并发安全，隔离 6.4s |
| `.env` | `EMBEDDING_DEVICE=cpu`（embedding 走 CPU，MPS 专供 reranker） | 消除双模型抢 MPS |
| `scripts/warmup.py` + `run_loadtest.sh` | 每档压测前预热触发模型加载 | 统计排除首次加载 |

## 6. 结论

1. **代码层优化全部到位**：DB 池、session 生命周期、reranker 并发安全 + 批处理、embedding→CPU，50 并发成功率从 55% 提升到 95%。
2. **系统真实容量**：这台 **16G 内存机器建议按 20-25 在线并发**规划（p50 ~25-30s，100% 成功）；30 并发为稳定上限，50 并发过载。
3. **最终瓶颈是硬件资源**：本地双模型（embedding/reranker）+ 50 并发使内存压缩至 8.4G，所有本地推理被拖慢 5-15 倍。批处理隔离验证 6.4s、进服务 34s，即内存压力所致。
4. **性能可预期基线**（修复后、预热、含 DeepSeek RAG 生成）：单条对话约 13-19s（低并发）到 25-38s（20-30 并发）。

## 7. 后续建议

- **硬件升级（根本解法）**：内存 ≥32G 或加专用 GPU；多机横向扩容 reranker 服务
- **如需支撑 50+ 并发**：关 rerank（`rerank.enabled=false`，省 MPS 大头负载）或用 GPU 集群
- **容量规划**：在线用户峰值建议 ≲ 25；按 0.5 条/s 峰值吞吐评估业务并发需求
- **可选项**：`uvicorn --workers N` 多进程（对 DeepSeek 网络 I/O 有助，但 MPS 单设备仍受限）

---

## 附：复现命令

```bash
# 容量档位（含预热，每档 5 分钟）
LT_LEVELS="10 20 30 50" bash apps/service/scripts/run_loadtest.sh

# 单档（如 20 并发），完整跑满每用户 5 条
LT_LEVELS="20" LT_RUN_TIME=900s bash apps/service/scripts/run_loadtest.sh
```

结果 CSV 在 `apps/service/scripts/loadtest_results/`（已 gitignore）。
