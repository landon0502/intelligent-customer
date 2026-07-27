# Task 2 Report: 添加后端认证相关依赖

## 状态: DONE

## 变更文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/service/pyproject.toml` | 修改 | 添加 sqlalchemy[asyncio], asyncmy, pyjwt, passlib[bcrypt], python-multipart 依赖 |
| `apps/service/uv.lock` | 自动更新 | uv sync 生成的锁文件 |
| `apps/service/.env` | 修改 | 追加 JWT_SECRET, JWT_EXPIRE_MINUTES, ADMIN_PASSWORD（被 .gitignore 排除，未入库） |
| `apps/service/app/core/config.py` | 修改 | Settings 类添加 JWT_SECRET, JWT_EXPIRE_MINUTES, ADMIN_PASSWORD 字段 |

## 验证结果

- `uv sync` 成功安装 6 个新包: asyncmy==0.2.11, bcrypt==5.0.0, greenlet==3.5.4, passlib==1.7.4, pyjwt==2.13.0, sqlalchemy==2.0.51
- 配置读取验证通过: `JWT_SECRET=intelligent-customer-jwt-secret-2026, JWT_EXPIRE=10080, ADMIN_PW=admin123456`

## 提交哈希

`925c56e` feat: add JWT, SQLAlchemy, and bcrypt dependencies with config

## 风险信号

- 无风险信号命中
- 注意: `.env` 文件被 `.gitignore` 排除未入库，部署时需确保环境变量已配置
