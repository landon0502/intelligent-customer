import { fetchClient } from "@/lib/fetch"
import { FetchPaginationParams, PaginationResponse } from "@/types/global"
// ========== 类型定义 ==========

export interface Document {
  id: string
  filename: string
  file_path: string
  file_type: string
  chunk_count: number
  status: "processing" | "ready" | "failed"
  uploaded_by: number | null
  uploaded_at: string
}

/**
 * 后端把上传目录挂成静态资源（file_path 是服务端绝对路径，浏览器拿不到）。
 * 挂载地址通过 NEXT_PUBLIC_FILE_BASE_URL 配置，未配置时回退到 API 地址 + /data/uploads。
 */
const FILE_BASE_URL = (
  process.env.NEXT_PUBLIC_FILE_BASE_URL ??
  `${process.env.NEXT_PUBLIC_API_URL}/data/uploads`
).replace(/\/+$/, "")

/** 由 file_path 拼出浏览器可直接访问的文件 URL（用于 PDF 预览） */
export function toDocumentFileUrl(filePath: string): string {
  const normalized = filePath.replace(/\\/g, "/")
  const idx = normalized.lastIndexOf("uploads/")
  const relative =
    idx >= 0
      ? normalized.slice(idx + "uploads/".length)
      : (normalized.split("/").pop() ?? "")
  return `${FILE_BASE_URL}/${relative}`
}

export interface KnowledgeQueryResult {
  chunks: Record<string, unknown>[]
  answer: string | null
  sources: Record<string, unknown>[] | null
}

export interface QueryKnowledgeParams {
  question: string
}

// ========== 知识库接口 ==========

export async function uploadDocumentApi(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  return fetchClient.post<{ document_id: number; status: string }>(
    "/knowledge/upload",
    formData
  )
}

export async function getDocumentsApi(params: FetchPaginationParams) {
  return fetchClient.get<PaginationResponse<Document>, FetchPaginationParams>(
    "/knowledge/documents",
    params
  )
}

export async function deleteDocumentApi(documentId: string) {
  return fetchClient.delete<{ success: boolean }>(
    `/knowledge/documents/${documentId}`
  )
}

export async function queryKnowledgeApi(question: string) {
  return fetchClient.post<KnowledgeQueryResult, QueryKnowledgeParams>(
    "/knowledge/query",
    {
      question,
    }
  )
}
