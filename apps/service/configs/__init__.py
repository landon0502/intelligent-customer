from configs.config import Settings

# 注意：不要在包初始化时导入 configs.provider / configs.registry。
# provider 依赖 schemas.system_config → database.mysql，而 database.mysql 依赖 configs.config，
# 包初始化时导入 provider 会在特定 import 顺序下形成循环（database.mysql 部分初始化）。
# 业务代码均通过 `from configs.provider import ...` 直接导入子模块，无需在此重导出。
