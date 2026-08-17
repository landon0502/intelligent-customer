import { useRequest } from "ahooks";
import { useMemo } from "react";
import { getToolsApi, updateToolApi, type ToolItem } from "@/services/tools";

export default function useToolServices() {
  // 工具列表（自动模式：挂载首拉；切换后手动重拉）
  const listControl = useRequest(getToolsApi, {});
  const { data: listData } = listControl;
  const tools = useMemo(() => listData?.data ?? [], [listData]);

  // 启停切换
  const toggleControl = useRequest(
    async (name: string, enabled: boolean) => updateToolApi(name, enabled),
    { manual: true },
  );

  async function toggleTool(name: string, enabled: boolean) {
    await toggleControl.runAsync(name, enabled);
    await listControl.run();
  }

  return {
    listControl,
    tools,
    toggleControl,
    toggleTool,
  };
}
