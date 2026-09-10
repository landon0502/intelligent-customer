import { useRequest } from "ahooks"
import { useMemo } from "react"
import {
  getDocumentsApi,
  uploadDocumentApi,
  deleteDocumentApi,
  queryKnowledgeApi,
} from "@/services/knowledge"

export default function useKnowledgeServices() {
  // 获取文档列表
  const documentsControl = useRequest(getDocumentsApi, { manual: true })
  const { data: docData } = documentsControl
  const documentData = useMemo(() => docData?.data, [docData])
  const documents = useMemo(() => documentData?.list ?? [], [documentData])
  // 服务端返回的文档总数（用于分页）
  const total = documentData?.total ?? 0
  // 当前页文档的分块合计（分页后前端只持有当前页）
  const totalChunks = useMemo(
    () => documents.reduce((sum, doc) => sum + doc.chunk_count, 0),
    [documents]
  )

  // 上传文档
  const uploadControl = useRequest(uploadDocumentApi, { manual: true })

  async function uploadDocument(file: File) {
    return uploadControl.runAsync(file)
  }

  // 删除文档
  const deleteControl = useRequest(deleteDocumentApi, { manual: true })

  async function removeDocument(documentId: string) {
    return deleteControl.runAsync(documentId)
  }

  // 检索测试
  const queryControl = useRequest(queryKnowledgeApi, { manual: true })
  const { data: queryData } = queryControl
  const searchResults = useMemo(() => {
    const chunks = queryData?.data?.chunks ?? []
    return chunks.map((chunk: Record<string, unknown>, i: number) => ({
      source: (chunk.source as string) ?? `结果 ${i + 1}`,
      content: (chunk.content as string) ?? "",
      similarity: (chunk.similarity as number) ?? 0,
    }))
  }, [queryData])

  async function searchKnowledge(question: string) {
    return queryControl.runAsync(question)
  }

  return {
    // 文档列表
    documentsControl,
    documents,
    total,
    totalChunks,
    // 上传
    uploadControl,
    uploadDocument,
    // 删除
    deleteControl,
    removeDocument,
    // 检索
    queryControl,
    searchResults,
    searchKnowledge,
  }
}
