# Task 1 实现报告：修复后端响应 code 与前端 SUCCESS_CODE 的兼容性

## 状态：DONE

## 变更文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/service/app/utils/response.py` | 修改 | `success()` 返回 `code: 0`（原 `code: 200`）；`ApiResponse.code` 默认值从 200 改为 0 |
| `apps/service/tests/test_response_utils.py` | 新建 | 3 个测试用例覆盖 success 默认/自定义 message 和 error 函数 |

## 测试结果

**命令：** `cd apps/service && uv run python -m pytest tests/test_response_utils.py -v`

**修改前（预期失败）：**
- `test_success_returns_code_zero` FAILED — `assert 200 == 0`
- `test_success_with_custom_message` FAILED — `assert 200 == 0`
- `test_error_returns_given_code` PASSED

**修改后（全部通过）：**
- `test_success_returns_code_zero` PASSED
- `test_success_with_custom_message` PASSED
- `test_error_returns_given_code` PASSED

3 passed in 0.01s

## 提交哈希

`8839033` — `fix: align backend success code to 0 for frontend FetchClient compatibility`

## 风险信号

- **公共API变更：是** — `success()` 返回的 `code` 字段从 200 变为 0，属于响应格式变更。但此变更正是为了修复与前端 FetchClient 的不兼容问题，前端 `SUCCESS_CODE = 0`，此前所有成功响应都被误判为业务错误，因此此变更是修复而非破坏。
- 跨模块/安全/并发/数据迁移：否
- diff > 200 行：否（2 files changed, 23 insertions, 2 deletions）

## 额外说明

- 安装了 `pytest` 作为开发依赖（`uv add --dev pytest`），已包含在 `uv.lock` 变更中但未单独 commit（pytest 是测试基础设施，非本 task 核心变更）
- `ApiResponse` 模型的 `code` 默认值也同步从 200 改为 0，保持一致性
