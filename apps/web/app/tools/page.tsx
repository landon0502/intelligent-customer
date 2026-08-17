"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Search, Wrench, ToggleLeft, ToggleRight } from "lucide-react"

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

// 模拟数据
interface ToolItem {
  id: number
  name: string
  triggerKey: string
  inputKey: string | null
  outputKey: string
  status: string
  implemented: boolean
}

const mockTools: ToolItem[] = [
  {
    id: 1,
    name: "knowledge_base_query",
    triggerKey: "toolTriggerKnowledge",
    inputKey: "toolInputQuestion",
    outputKey: "toolOutputChunks",
    status: "enabled",
    implemented: true,
  },
  {
    id: 2,
    name: "enterprise_query",
    triggerKey: "toolTriggerEnterprise",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputBusinessInfo",
    status: "enabled",
    implemented: true,
  },
  {
    id: 3,
    name: "ticket_submit",
    triggerKey: "toolTriggerSubmit",
    inputKey: "toolInputSubmit",
    outputKey: "toolOutputTicket",
    status: "enabled",
    implemented: true,
  },
  {
    id: 4,
    name: "ticket_status",
    triggerKey: "toolTriggerStatus",
    inputKey: "toolInputServiceCode",
    outputKey: "toolOutputTicket",
    status: "enabled",
    implemented: false,
  },
  {
    id: 5,
    name: "transfer_human",
    triggerKey: "toolTriggerHuman",
    inputKey: null,
    outputKey: "toolOutputNotify",
    status: "enabled",
    implemented: true,
  },
  {
    id: 6,
    name: "clarify",
    triggerKey: "toolTriggerClarify",
    inputKey: null,
    outputKey: "toolOutputQuestion",
    status: "enabled",
    implemented: true,
  },
]

export default function ToolsPage() {
  const t = useTranslations("tools")
  const [searchQuery, setSearchQuery] = useState("")
  const [tools, setTools] = useState(mockTools)

  const filteredTools = tools.filter(
    (tool) =>
      !searchQuery ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  function toggleTool(id: number) {
    setTools((prev) =>
      prev.map((tool) =>
        tool.id === id
          ? {
              ...tool,
              status: tool.status === "enabled" ? "disabled" : "enabled",
            }
          : tool
      )
    )
  }

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("toolCount", { count: tools.length })} ·{" "}
            {t("enabledCount", {
              count: tools.filter((tool) => tool.status === "enabled").length,
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
              {filteredTools.map((tool) => (
                <TableRow key={tool.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <Wrench className="size-4 text-muted-foreground" />
                      <code className="text-sm">{tool.name}</code>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    {t(tool.triggerKey as Parameters<typeof t>[0])}
                  </TableCell>
                  <TableCell className="text-sm">
                    {tool.inputKey
                      ? t(tool.inputKey as Parameters<typeof t>[0])
                      : "—"}
                  </TableCell>
                  <TableCell className="text-sm">
                    {t(tool.outputKey as Parameters<typeof t>[0])}
                  </TableCell>
                  <TableCell>
                    {tool.implemented ? (
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
                      variant={
                        tool.status === "enabled" ? "default" : "outline"
                      }
                      className={
                        tool.status === "enabled"
                          ? "bg-primary/10 text-primary hover:bg-primary/10"
                          : ""
                      }
                    >
                      {tool.status === "enabled" ? t("enabled") : t("disabled")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleTool(tool.id)}
                    >
                      {tool.status === "enabled" ? (
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
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
