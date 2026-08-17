"use client"

import { useCallback, useState } from "react"
import { useTranslations } from "next-intl"
import { Search, Wrench, ToggleLeft, ToggleRight } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import useToolServices from "./useServices"

// 前端静态展示元数据（i18n 键映射 + 实现标记），与后端返回的 name/enabled 合并渲染
interface ToolMeta {
  triggerKey: string
  inputKey: string | null
  outputKey: string
  implemented: boolean
}

const toolMeta: Record<string, ToolMeta> = {
  knowledge_base_query: {
    triggerKey: "toolTriggerKnowledge",
    inputKey: "toolInputQuestion",
    outputKey: "toolOutputChunks",
    implemented: true,
  },
  enterprise_query: {
    triggerKey: "toolTriggerEnterprise",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputBusinessInfo",
    implemented: true,
  },
  ticket_submit: {
    triggerKey: "toolTriggerSubmit",
    inputKey: "toolInputSubmit",
    outputKey: "toolOutputTicket",
    implemented: true,
  },
  ticket_status: {
    triggerKey: "toolTriggerStatus",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputTicket",
    implemented: true,
  },
  transfer_human: {
    triggerKey: "toolTriggerHuman",
    inputKey: null,
    outputKey: "toolOutputNotify",
    implemented: true,
  },
  clarify: {
    triggerKey: "toolTriggerClarify",
    inputKey: null,
    outputKey: "toolOutputQuestion",
    implemented: true,
  },
}

// 兜底工具：后端硬校验不可禁用，前端行开关置灰
const GUARDED_TOOLS = new Set(["transfer_human", "clarify"])

export default function ToolsPage() {
  const t = useTranslations("tools")
  const { tools, toggleTool } = useToolServices()

  const [searchQuery, setSearchQuery] = useState("")

  const filteredTools = tools.filter(
    (tool) =>
      !searchQuery ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleToggle = useCallback(
    async (name: string, enabled: boolean) => {
      try {
        await toggleTool(name, enabled)
        toast.success(t("toggleSuccess"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [toggleTool, t]
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("toolCount", { count: tools.length })} ·{" "}
            {t("enabledCount", {
              count: tools.filter((tool) => tool.enabled).length,
            })}
          </p>
        </div>
        <div className="relative">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t("searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-60 pl-9"
          />
        </div>
      </div>

      {/* 工具表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("colName")}</TableHead>
                <TableHead>{t("colTrigger")}</TableHead>
                <TableHead>{t("colInput")}</TableHead>
                <TableHead>{t("colOutput")}</TableHead>
                <TableHead>{t("colImplemented")}</TableHead>
                <TableHead>{t("colStatus")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTools.map((tool) => {
                const meta = toolMeta[tool.name]
                const isGuarded = GUARDED_TOOLS.has(tool.name)
                return (
                  <TableRow key={tool.name}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Wrench className="size-4 text-muted-foreground" />
                        <code className="text-sm">{tool.name}</code>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      {meta
                        ? t(meta.triggerKey as Parameters<typeof t>[0])
                        : tool.description}
                    </TableCell>
                    <TableCell className="text-sm">
                      {meta?.inputKey
                        ? t(meta.inputKey as Parameters<typeof t>[0])
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {meta
                        ? t(meta.outputKey as Parameters<typeof t>[0])
                        : "—"}
                    </TableCell>
                    <TableCell>
                      {meta?.implemented ? (
                        <Badge
                          variant="default"
                          className="bg-green-100 text-green-700 hover:bg-green-100"
                        >
                          {t("implemented")}
                        </Badge>
                      ) : (
                        <Badge
                          variant="secondary"
                          className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100"
                        >
                          {t("simulated")}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={tool.enabled ? "default" : "outline"}
                        className={
                          tool.enabled
                            ? "bg-primary/10 text-primary hover:bg-primary/10"
                            : ""
                        }
                      >
                        {tool.enabled ? t("enabled") : t("disabled")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isGuarded}
                        title={isGuarded ? t("guardedToolTip") : undefined}
                        onClick={() => handleToggle(tool.name, !tool.enabled)}
                      >
                        {tool.enabled ? (
                          <>
                            <ToggleRight className="mr-1 size-4 text-primary" />
                            {t("disable")}
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="mr-1 size-4 text-muted-foreground" />
                            {t("enable")}
                          </>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
