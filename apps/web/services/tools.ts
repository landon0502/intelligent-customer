import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface ToolItem {
  name: string
  description: string
  enabled: boolean
}

export interface ToolUpdateResult {
  name: string
  enabled: boolean
  refresh_ok: boolean
}

// ========== 工具启停接口 ==========

export async function getToolsApi() {
  return fetchClient.get<ToolItem[]>("/tools")
}

export async function updateToolApi(name: string, enabled: boolean) {
  return fetchClient.patch<ToolUpdateResult>(`/tools/${name}`, { enabled })
}
