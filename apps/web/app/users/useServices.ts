import { useRequest } from "ahooks";
import { useMemo } from "react";
import {
  getUsersApi,
  createUserApi,
  deleteUserApi,
  type User,
} from "@/services/users";

export default function useUserServices() {
  // 用户列表（自动模式：挂载首拉；create/delete 后手动重拉）
  const listControl = useRequest(getUsersApi, {});
  const { data: listData } = listControl;
  const users = useMemo(() => listData?.data ?? [], [listData]);

  // 创建用户
  const createControl = useRequest(
    async (username: string, password: string, role: string) =>
      createUserApi(username, password, role),
    { manual: true },
  );

  async function createUser(username: string, password: string, role: string) {
    await createControl.runAsync(username, password, role);
    await listControl.run();
  }

  // 删除用户
  const deleteControl = useRequest(deleteUserApi, { manual: true });

  async function removeUser(id: number) {
    await deleteControl.runAsync(id);
    await listControl.run();
  }

  return {
    listControl,
    users,
    createControl,
    createUser,
    deleteControl,
    removeUser,
  };
}
