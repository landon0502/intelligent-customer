"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Upload, Search, Trash2, FileText, File, FileImage } from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@intelligent-customer/ui/components/card"
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

// 模拟数据
const mockDocuments = [
  { id: 1, filename: "退货政策.pdf", type: "PDF", chunks: 32, status: "ready", uploader: "admin", uploadedAt: "2026-07-20 10:30" },
  { id: 2, filename: "产品介绍.docx", type: "Word", chunks: 28, status: "ready", uploader: "admin", uploadedAt: "2026-07-20 10:28" },
  { id: 3, filename: "配送说明.pdf", type: "PDF", chunks: 24, status: "ready", uploader: "admin", uploadedAt: "2026-07-19 16:45" },
  { id: 4, filename: "常见问题.txt", type: "TXT", chunks: 18, status: "ready", uploader: "admin", uploadedAt: "2026-07-19 14:20" },
  { id: 5, filename: "会员权益说明.pdf", type: "PDF", chunks: 0, status: "processing", uploader: "admin", uploadedAt: "2026-07-24 09:15" },
]

const mockSearchResults = [
  { source: "退货政策.pdf [块#3]", content: "退款将在收到退货商品后3个工作日内原路返回...", similarity: 0.92 },
  { source: "退货政策.pdf [块#1]", content: "商品签收后7天内可以申请无理由退货...", similarity: 0.87 },
  { source: "配送说明.pdf [块#2]", content: "退货商品请使用原包装寄回...", similarity: 0.71 },
]

function FileTypeIcon({ type }: { type: string }) {
  switch (type) {
    case "PDF": return <FileImage className="size-4 text-red-500" />
    case "Word": return <File className="size-4 text-blue-500" />
    default: return <FileText className="size-4 text-orange-500" />
  }
}

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("knowledge")
  if (status === "ready") {
    return <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">{t("statusReady")}</Badge>
  }
  return <Badge variant="secondary" className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100">{t("statusProcessing")}</Badge>
}

export default function KnowledgePage() {
  const t = useTranslations("knowledge")
  const tCommon = useTranslations("common")
  const [searchQuery, setSearchQuery] = useState("")
  const [retrievalQuery, setRetrievalQuery] = useState("退货需要多长时间？")
  const [showResults, setShowResults] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)

  const filteredDocs = mockDocuments.filter(
    (doc) => !searchQuery || doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const totalChunks = mockDocuments.reduce((sum, doc) => sum + doc.chunks, 0)

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* 标题栏 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">{t("title")}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t("docCount", { count: mockDocuments.length })} · {t("chunkCount", { count: totalChunks })}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder={t("searchPlaceholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 w-60"
              />
            </div>
            <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
              <DialogTrigger render={<Button><Upload className="size-4 mr-2" />{t("upload")}</Button>}>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t("uploadTitle")}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="border-2 border-dashed rounded-lg p-8 text-center">
                    <Upload className="size-8 mx-auto text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">{t("uploadHint")}</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF / Word / TXT</p>
                  </div>
                  <Button className="w-full" onClick={() => setUploadOpen(false)}>
                    {t("uploadConfirm")}
                  </Button>
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
                  <TableHead>{t("colUploader")}</TableHead>
                  <TableHead>{t("colUploadedAt")}</TableHead>
                  <TableHead className="text-right">{t("colActions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocs.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileTypeIcon type={doc.type} />
                        {doc.filename}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{doc.type}</Badge>
                    </TableCell>
                    <TableCell>{doc.chunks || "—"}</TableCell>
                    <TableCell><StatusBadge status={doc.status} /></TableCell>
                    <TableCell>{doc.uploader}</TableCell>
                    <TableCell className="text-muted-foreground">{doc.uploadedAt}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" className="text-destructive hover:text-destructive">
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
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
              />
              <Button onClick={() => setShowResults(true)}>{t("retrievalSearch")}</Button>
            </div>
            {showResults && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">{t("retrievalResult")}</p>
                {mockSearchResults.map((result, i) => (
                  <div key={i} className="p-3 bg-primary/5 rounded-md">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{result.source}</span>
                      <span className="text-xs text-primary">{t("similarity")}: {result.similarity}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
