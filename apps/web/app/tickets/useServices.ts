import { useRequest } from "ahooks";
import { useCallback, useMemo, useState } from "react";
import {
  getTicketsApi,
  updateTicketStatusApi,
  type TicketStatus,
} from "@/services/tickets";

/** 每页条数，与后端 Query(alias="pageSize") 对应 */
export const PAGE_SIZE = 10;

export default function useTicketServices() {
  // 状态筛选（"" 表示全部）
  const [statusFilter, setStatusFilterState] = useState<TicketStatus | "">("");
  const [page, setPage] = useState(1);

  // 工单列表（跟随状态筛选与页码；自动模式 + refreshDeps：挂载首拉、筛选/翻页变化自动重拉）。
  // 不用 manual + useEffect([statusFilter, listControl])：ahooks 每次渲染返回新的
  // listControl 对象身份 + run() 无条件 setState 强制重渲染，会构成无限重拉取循环
  const listControl = useRequest(
    () =>
      getTicketsApi({
        status: statusFilter || undefined,
        page,
        pageSize: PAGE_SIZE,
      }),
    { refreshDeps: [statusFilter, page] }
  );
  const { data: listData } = listControl;
  const tickets = useMemo(() => listData?.data?.list ?? [], [listData]);
  const total = listData?.data?.total ?? 0;

  // 切换筛选时回到第 1 页（两次 setState 同批次，只触发一次重拉）
  const setStatusFilter = useCallback((next: TicketStatus | "") => {
    setStatusFilterState(next);
    setPage(1);
  }, []);

  // 更新状态
  const updateControl = useRequest(updateTicketStatusApi, { manual: true });

  async function updateStatus(ticketNo: string, status: TicketStatus) {
    await updateControl.runAsync(ticketNo, status);
    await listControl.run();
  }

  return {
    statusFilter,
    setStatusFilter,
    page,
    setPage,
    pageSize: PAGE_SIZE,
    listControl,
    tickets,
    total,
    updateControl,
    updateStatus,
  };
}
