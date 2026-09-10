"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useTranslations } from "next-intl"
import { Upload, Search, Trash2, FileText, File, FileImage } from "lucide-react"
import useKnowledgeServices from "./useServices"
import { toDocumentFileUrl } from "@/services/knowledge"
import type { FetchPaginationParams } from "@/types/global"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@intelligent-customer/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@intelligent-customer/ui/components/dialog"
import { ConfirmDialog } from "@/components/confirm-dialog"
import { PaginationFooter } from "@/components/pagination-footer"
import { toast } from "sonner"

function FileTypeIcon({ type }: { type: string }) {
  switch (type.toLowerCase()) {
    case "pdf":
      return <FileImage className="size-4 text-red-500" />
    case "docx":
    case "doc":
      return <File className="size-4 text-blue-500" />
    default:
      return <FileText className="size-4 text-orange-500" />
  }
}

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("knowledge")
  if (status === "ready") {
    return (
      <Badge
        variant="default"
        className="bg-green-100 text-green-700 hover:bg-green-100"
      >
        {t("statusReady")}
      </Badge>
    )
  }
  if (status === "failed") {
    return <Badge variant="destructive">{t("statusFailed")}</Badge>
  }
  return (
    <Badge
      variant="secondary"
      className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
    >
      {t("statusProcessing")}
    </Badge>
  )
}

function formatUploadTime(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

/** 每页条数，与后端 Query(alias="pageSize") 对应 */
const PAGE_SIZE = 10

export default function KnowledgePage() {
  const t = useTranslations("knowledge")

  const {
    documentsControl,
    documents,
    total,
    totalChunks,
    uploadControl,
    uploadDocument,
    deleteControl,
    removeDocument,
    queryControl,
    searchResults,
    searchKnowledge,
  } = useKnowledgeServices()

  // run 由 ahooks useMemoizedFn 包装，引用稳定，可安全作为 effect 依赖
  const { run: runDocuments } = documentsControl

  const [searchQuery, setSearchQuery] = useState("")
  const [retrievalQuery, setRetrievalQuery] = useState("")
  const [showResults, setShowResults] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string
    filename: string
  } | null>(null)

  const [page, setPage] = useState(1)
  // 已提交给后端的搜索关键字（回车后才写入）
  const [keyword, setKeyword] = useState("")

  const fetchParams = useMemo<FetchPaginationParams>(
    () => ({ page, pageSize: PAGE_SIZE, keyword: keyword || undefined }),
    [page, keyword]
  )

  // 回车后才提交搜索：写入关键字并回到第 1 页
  const handleSearch = useCallback(() => {
    const next = searchQuery.trim()
    if (next === keyword && page === 1) return
    setKeyword(next)
    setPage(1)
  }, [searchQuery, keyword, page])

  // 页面加载 / 翻页 / 关键字变化时拉取文档列表
  useEffect(() => {
    runDocuments(fetchParams)
  }, [fetchParams, runDocuments])

  // 上传的异步处理在接口返回后才完成（processing → ready/failed），
  // 这里轮询文档列表直至全部处理完成或超时，让状态自动反映到 UI
  const hasProcessing = documents.some((doc) => doc.status === "processing")
  useEffect(() => {
    if (!hasProcessing) return
    const start = Date.now()
    const timer = setInterval(() => {
      if (Date.now() - start > 60_000) {
        clearInterval(timer)
        return
      }
      runDocuments(fetchParams)
    }, 2000)
    return () => clearInterval(timer)
  }, [hasProcessing, fetchParams, runDocuments])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // 上传文档
  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return

      try {
        await uploadDocument(file)
        toast.success(t("uploadSuccess"))
        setUploadOpen(false)
        // 服务端按上传时间倒序，新文档在第 1 页
        if (page === 1) runDocuments(fetchParams)
        else setPage(1)
      } catch {
        toast.error(t("uploadFailed"))
      }
    },
    [t, uploadDocument, page, runDocuments, fetchParams]
  )

  // 删除文档
  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await removeDocument(id)
        toast.success(t("deleteSuccess"))
        setDeleteTarget(null)
        // 删掉当前页最后一条时回退一页，避免停在空页
        if (documents.length === 1 && page > 1) setPage(page - 1)
        else runDocuments(fetchParams)
      } catch {
        toast.error(t("deleteFailed"))
      }
    },
    [t, removeDocument, documents.length, page, runDocuments, fetchParams]
  )

  // 检索测试
  const handleRetrievalSearch = useCallback(async () => {
    if (!retrievalQuery.trim()) return
    setShowResults(true)
    try {
      await searchKnowledge(retrievalQuery)
    } catch {
      // 错误由拦截器处理
    }
  }, [retrievalQuery, searchKnowledge])

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("docCount", { count: total })} ·{" "}
            {t("chunkCount", { count: totalChunks })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-60 pl-9"
            />
          </div>
          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger
              render={
                <Button>
                  <Upload className="mr-2 size-4" />
                  {t("upload")}
                </Button>
              }
            ></DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("uploadTitle")}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="rounded-lg border-2 border-dashed p-8 text-center">
                  <Upload className="mx-auto mb-2 size-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {t("uploadHint")}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    PDF / Word / TXT
                  </p>
                  <Input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    onChange={handleUpload}
                    disabled={uploadControl.loading}
                    className="mt-4"
                  />
                </div>
                {uploadControl.loading && (
                  <p className="text-center text-sm text-muted-foreground">
                    {t("uploading")}
                  </p>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* 文档表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("colFilename")}</TableHead>
                <TableHead>{t("colType")}</TableHead>
                <TableHead>{t("colChunks")}</TableHead>
                <TableHead>{t("colStatus")}</TableHead>
                <TableHead>{t("colUploadedAt")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-muted-foreground"
                  >
                    {t("noDocuments")}
                  </TableCell>
                </TableRow>
              ) : (
                documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileTypeIcon type={doc.file_type} />
                        <a
                          href={toDocumentFileUrl(doc.file_path)}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={t("previewFile")}
                          className="text-blue-600 underline-offset-4 hover:underline dark:text-blue-400"
                        >
                          {doc.filename}
                        </a>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {doc.file_type.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>{doc.chunk_count || "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={doc.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatUploadTime(doc.uploaded_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-destructive hover:text-destructive"
                        disabled={
                          deleteControl.params?.[0] === doc.id &&
                          deleteControl.loading
                        }
                        onClick={() => setDeleteTarget(doc)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
        <PaginationFooter
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </Card>

      {/* 检索测试 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("retrievalTest")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <Input
              placeholder={t("retrievalPlaceholder")}
              value={retrievalQuery}
              onChange={(e) => setRetrievalQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRetrievalSearch()}
            />
            <Button
              onClick={handleRetrievalSearch}
              disabled={queryControl.loading}
            >
              {queryControl.loading ? t("searching") : t("retrievalSearch")}
            </Button>
          </div>
          {showResults && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                {t("retrievalResult")}
              </p>
              {searchResults.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  {t("noResults")}
                </p>
              ) : (
                searchResults.map((result, i) => (
                  <div key={i} className="rounded-md bg-primary/5 p-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {result.source}
                      </span>
                      {result.similarity > 0 && (
                        <span className="text-xs text-primary">
                          {t("similarity")}: {result.similarity.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {result.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={t("deleteDocTitle")}
        description={t("deleteDocDesc", {
          filename: deleteTarget?.filename ?? "",
        })}
        loading={deleteControl.loading}
        onConfirm={() => deleteTarget && handleDelete(deleteTarget.id)}
      />
    </div>
  )
}
