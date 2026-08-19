#!/usr/bin/env bash
# 并发压测 runner —— 依次跑 50 / 80 / 100 并发档位，每用户 5 条消息，
# 输出各档 CSV 并打印对比汇总（RPS / 总耗时 / TTFB / 错误率）。
#
# 用法:
#   bash apps/service/scripts/run_loadtest.sh
#
# 可调环境变量:
#   LT_LEVELS        并发档位，默认 "50 80 100"
#   LT_SPAWN_RATE    每秒启动用户数，默认 10
#   LT_RUN_TIME      单档运行时长上限，默认 600s（系统 RAG 聊天较慢，放宽时间）
#   LT_MSGS_PER_USER 每用户消息数，默认 5（0 = 持续发送直到 run-time）
#   LT_HOST          服务地址，默认 http://127.0.0.1:8009
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SERVICE_DIR"

VENV="$SERVICE_DIR/.venv/bin"
LOCUST="$VENV/locust"
RESULTS_DIR="$SCRIPT_DIR/loadtest_results"
mkdir -p "$RESULTS_DIR"

LEVELS="${LT_LEVELS:-50 80 100}"
SPAWN_RATE="${LT_SPAWN_RATE:-10}"
RUN_TIME="${LT_RUN_TIME:-600s}"
MSGS_PER_USER="${LT_MSGS_PER_USER:-5}"
HOST="${LT_HOST:-http://127.0.0.1:8009}"

echo "== 压测目标: $HOST"
echo "== 并发档位: $LEVELS   每用户消息数: $MSGS_PER_USER   单档上限: $RUN_TIME   启动速率: ${SPAWN_RATE}/s"
echo "== 结果目录: $RESULTS_DIR"

for u in $LEVELS; do
  echo
  echo "===== [$u 并发用户] $(date '+%H:%M:%S') ====="
  # 预热：发一条 RAG 消息触发 reranker/embedding 加载，排除首次加载时间对统计的污染
  echo "--- 预热（触发模型加载，不计入统计） ---"
  "$VENV/python" "$SCRIPT_DIR/warmup.py" --host "$HOST" || echo "[warmup] 预热失败，继续压测"
  STAGE_LOG="$RESULTS_DIR/r${u}.log"
  # 各档输出写独立日志文件（避免管道截断导致 Locust CSV writer 报 closed-file）
  "$LOCUST" -f "$SCRIPT_DIR/locustfile.py" \
    --headless -u "$u" -r "$SPAWN_RATE" --run-time "$RUN_TIME" \
    --host "$HOST" \
    --csv "$RESULTS_DIR/r${u}" --csv-full-history \
    > "$STAGE_LOG" 2>&1 || true
  tail -4 "$STAGE_LOG"
done

echo
echo "=================== 汇总对比（/api/chat/send） ==================="
"$VENV/python" - "$RESULTS_DIR" <<'PY'
import csv
import glob
import os
import sys

results_dir = sys.argv[1]
rows = []
for f in glob.glob(os.path.join(results_dir, "r*_stats.csv")):
    u = os.path.basename(f).split("r")[1].split("_")[0]
    rec = {"users": u, "POST": None, "STREAM": None}
    with open(f) as fh:
        for r in csv.DictReader(fh):
            if r.get("Name") != "/api/chat/send":
                continue
            rec[r.get("Type", "")] = r
    if rec["STREAM"] or rec["POST"]:
        rows.append(rec)

def g(rec, key, col):
    try:
        return rec[key][col]
    except (KeyError, TypeError):
        return "-"

rows.sort(key=lambda r: int(r["users"]))
# STREAM = 完整流耗时（用户感知总延迟）；POST = 内置 TTFB（Locust 对 stream 的计时）
hdr = (f"{'并发':>4} {'RPS':>6} {'请求':>6} {'失败':>4} {'错误%':>6} "
       f"{'总均ms':>7} {'总p50':>6} {'总p90':>6} {'总p95':>6} {'总p99':>6} {'总最长s':>7} "
       f"{'TTFB均ms':>8} {'TTFBp90':>8}")
print(hdr)
print("-" * len(hdr))
for r in rows:
    mx = g(r, "STREAM", "Max Response Time")
    req = g(r, 'POST', 'Request Count')
    fail = g(r, 'POST', 'Failure Count')
    err = f"{float(fail)/float(req)*100:.1f}" if req != '-' and fail != '-' else "-"
    print(f"{r['users']:>4} {g(r,'POST','Requests/s'):>6} "
          f"{req:>6} {fail:>4} {err:>6} "
          f"{g(r,'STREAM','Average Response Time'):>7} {g(r,'STREAM','50%'):>6} "
          f"{g(r,'STREAM','90%'):>6} {g(r,'STREAM','95%'):>6} {g(r,'STREAM','99%'):>6} "
          f"{float(mx)/1000 if mx != '-' else '-':>7.1f} "
          f"{g(r,'POST','Average Response Time'):>8} {g(r,'POST','90%'):>8}")
print()
print("说明: 总=完整SSE流耗时(检索+生成+传输), TTFB=首事件耗时(内置POST行=Locust对stream的计时)")
print("      错误% 含 HTTP非200 / SSE error / 断流 / 超时")
print("CSV 明细: " + results_dir + "/r{档位}_*.csv")
PY
