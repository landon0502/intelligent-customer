import { useRequest } from "ahooks";
import { useMemo, useState } from "react";
import {
  getTicketsApi,
  updateTicketStatusApi,
  type Ticket,
  type TicketStatus,
} from "@/services/tickets";

export default function useTicketServices() {
  // 状态筛选（"" 表示全部）
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "">("");

  // 工单列表（跟随状态筛选；manual 模式由页面 useEffect 触发）
  const listControl = useRequest(() => getTicketsApi(statusFilter), {
    manual: true,
  });
  const { data: listData } = listControl;
  const tickets = useMemo(() => listData?.data ?? [], [listData]);

  // 更新状态
  const updateControl = useRequest(updateTicketStatusApi, { manual: true });

  async function updateStatus(ticketNo: string, status: TicketStatus) {
    await updateControl.runAsync(ticketNo, status);
    await listControl.run();
  }

  return {
    statusFilter,
    setStatusFilter,
    listControl,
    tickets,
    updateControl,
    updateStatus,
  };
}
