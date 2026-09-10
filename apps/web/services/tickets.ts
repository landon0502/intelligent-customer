import { fetchClient } from "@/lib/fetch"
import type { FetchPaginationParams, PaginationResponse } from "@/types/global"

// ========== 类型定义 ==========

export type TicketStatus = "open" | "processing" | "closed"

export interface Ticket {
  id: number
  ticket_no: string
  user_id: number | null
  username: string | null
  conversation_id: number | null
  business_code: string
  content: string
  status: TicketStatus
  created_at: string
  updated_at: string
}

export interface GetTicketsParams extends FetchPaginationParams {
  status?: TicketStatus
}

export interface UpdateTicketStatusParams {
  status: TicketStatus
}

// ========== 工单接口 ==========

export async function getTicketsApi({
  status,
  page,
  pageSize,
}: GetTicketsParams) {
  return fetchClient.get<PaginationResponse<Ticket>, GetTicketsParams>(
    "/tickets",
    { status: status || undefined, page, pageSize }
  )
}

export async function updateTicketStatusApi(ticketNo: string, status: TicketStatus) {
  return fetchClient.patch<Ticket, UpdateTicketStatusParams>(
    `/tickets/${ticketNo}/status`,
    { status }
  )
}
