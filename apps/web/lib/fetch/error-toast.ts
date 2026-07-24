import { toast } from "sonner";
import type { FetchClient } from "@intelligent-customer/fetch-client";
import { HTTP_STATUS } from "./config";

const STATUS_MESSAGES: Record<number, string> = {
  [HTTP_STATUS.BAD_REQUEST]: "请求参数有误",
  [HTTP_STATUS.FORBIDDEN]: "没有权限执行此操作",
  [HTTP_STATUS.NOT_FOUND]: "请求的资源不存在",
  [HTTP_STATUS.TOO_MANY_REQUESTS]: "请求过于频繁，请稍后重试",
  [HTTP_STATUS.INTERNAL_SERVER_ERROR]: "服务器异常，请稍后重试",
  [HTTP_STATUS.SERVICE_UNAVAILABLE]: "服务暂不可用，请稍后重试",
};

/** 在 FetchClient 上注册全局响应拦截器，非 2xx / 401 时弹 toast */
export function setupErrorToast(client: FetchClient): () => void {
  return client.useResponseInterceptor(async (response, ctx) => {
    if (response.ok || ctx.config.skipErrorHandler) return response;

    // 401 由 AuthGuard 处理跳转，不弹 toast
    if (response.status === HTTP_STATUS.UNAUTHORIZED) return response;

    // 尝试读取服务端返回的 message
    let message = STATUS_MESSAGES[response.status] || null;
    try {
      const body = await response.clone().json();
      if (body?.message) message = body.message;
    } catch {
      // 无法解析 body，使用状态码默认消息
    }

    if (message) toast.error(message);
    return response;
  });
}
