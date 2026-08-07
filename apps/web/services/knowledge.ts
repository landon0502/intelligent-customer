import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface Document {
  id: number
  filename: string
  file_type: string
  chunk_count: number
  status: "processing" | "ready" | "failed"
  uploaded_by: number | null
  uploaded_at: string
}

export interface KnowledgeQueryResult {
  chunks: Record<string, unknown>[]
  answer: string | null
  sources: Record<string, unknown>[] | null
}

// ========== 知识库接口 ==========

export async function uploadDocumentApi(file: File) {
  const formData = new FormData()
  formData.append("file", file)
  return fetchClient.post<{ document_id: number; status: string }>("/knowledge/upload", formData)
}

export async function getDocumentsApi() {
  return fetchClient.get<Document[]>("/knowledge/documents")
}

export async function deleteDocumentApi(documentId: number) {
  return fetchClient.delete<{ success: boolean }>(`/knowledge/documents/${documentId}`)
}

export async function queryKnowledgeApi(question: string) {
  return fetchClient.post<KnowledgeQueryResult>("/knowledge/query", { question })
}
