import { fetchClient } from "@/lib/fetch"

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

// ========== 工单接口 ==========

export async function getTicketsApi(status?: TicketStatus | "") {
  return fetchClient.get<Ticket[]>(
    "/tickets",
    status ? { status } : undefined
  )
}

export async function updateTicketStatusApi(ticketNo: string, status: TicketStatus) {
  return fetchClient.patch<Ticket>(`/tickets/${ticketNo}/status`, { status })
}
