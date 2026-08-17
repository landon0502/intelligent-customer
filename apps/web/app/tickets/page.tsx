"use client"

import { useCallback, useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import useTicketServices from "./useServices"

import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import { Badge } from "@intelligent-customer/ui/components/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"
import { toast } from "sonner"
import type { TicketStatus } from "@/services/tickets"

const STATUS_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "all", labelKey: "statusAll" },
  { value: "open", labelKey: "statusOpen" },
  { value: "processing", labelKey: "statusProcessing" },
  { value: "closed", labelKey: "statusClosed" },
]

function StatusBadge({ status }: { status: TicketStatus }) {
  const t = useTranslations("tickets")
  if (status === "open") {
    return (
      <Badge variant="secondary" className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100">
        {t("statusOpen")}
      </Badge>
    )
  }
  if (status === "processing") {
    return (
      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
        {t("statusProcessing")}
      </Badge>
    )
  }
  return (
    <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
      {t("statusClosed")}
    </Badge>
  )
}

function formatCreatedAt(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
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

export default function TicketsPage() {
  const t = useTranslations("tickets")
  const {
    statusFilter,
    setStatusFilter,
    listControl,
    tickets,
    updateControl,
    updateStatus,
  } = useTicketServices()

  // 状态筛选变化时重新拉取
  useEffect(() => {
    listControl.run()
  }, [statusFilter, listControl])

  const handleStatusChange = useCallback(
    async (ticketNo: string, status: TicketStatus) => {
      try {
        await updateStatus(ticketNo, status)
        toast.success(t("statusUpdated"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [updateStatus, t],
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("ticketCount", { count: tickets.length })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={statusFilter || "all"}
            onValueChange={(v) => setStatusFilter(v === "all" ? "" : (v as TicketStatus))}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 工单表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("colTicketNo")}</TableHead>
                <TableHead>{t("colBusiness")}</TableHead>
                <TableHead>{t("colUser")}</TableHead>
                <TableHead>{t("colStatus")}</TableHead>
                <TableHead>{t("colCreatedAt")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                    {t("noTickets")}
                  </TableCell>
                </TableRow>
              ) : (
                tickets.map((ticket) => (
                  <TableRow key={ticket.id}>
                    <TableCell className="font-medium">{ticket.ticket_no}</TableCell>
                    <TableCell>{ticket.business_code}</TableCell>
                    <TableCell>{ticket.username ?? ticket.user_id ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={ticket.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatCreatedAt(ticket.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={ticket.status}
                        disabled={updateControl.loading}
                        onValueChange={(v) =>
                          handleStatusChange(ticket.ticket_no, v as TicketStatus)
                        }
                      >
                        <SelectTrigger className="h-8 w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="open">{t("statusOpen")}</SelectItem>
                          <SelectItem value="processing">{t("statusProcessing")}</SelectItem>
                          <SelectItem value="closed">{t("statusClosed")}</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
