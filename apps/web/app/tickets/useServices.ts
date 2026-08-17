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

  // 工单列表（跟随状态筛选；自动模式 + refreshDeps：挂载首拉、筛选变化自动重拉）。
  // 不用 manual + useEffect([statusFilter, listControl])：ahooks 每次渲染返回新的
  // listControl 对象身份 + run() 无条件 setState 强制重渲染，会构成无限重拉取循环
  const listControl = useRequest(() => getTicketsApi(statusFilter), {
    refreshDeps: [statusFilter],
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
