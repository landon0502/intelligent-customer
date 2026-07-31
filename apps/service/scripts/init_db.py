"""
数据库初始化脚本 —— 创建所有表并插入种子数据。

用法:
    cd apps/service
    python scripts/init_db.py
"""

import asyncio
import sys
import os

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import mysql
import database.models  # noqa: F401  — 注册所有 ORM 模型
from database.session import get_db
from services.auth import seed_admin_user
from configs.config import settings


async def init_database():
    """创建所有数据表并插入种子数据"""
    print("=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)

    # 1. 创建所有表
    print("\n[1/2] 创建数据表...")
    async with mysql.engine.begin() as conn:
        await conn.run_sync(mysql.Base.metadata.create_all)
    print("✓ 所有数据表创建完成")
    print(f"  - users（用户表）")
    print(f"  - conversations（会话表）")
    print(f"  - messages（消息表）")
    print(f"  - documents（文档表）")

    # 2. 插入种子数据
    print("\n[2/2] 插入种子数据...")
    async for db in get_db():
        await seed_admin_user(db)
    print("✓ 管理员用户(admin)已就绪")

    # 清理
    await mysql.engine.dispose()

    print("\n" + "=" * 50)
    print("数据库初始化完成！")
    print(f"连接地址: {settings.database_url}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(init_database())
