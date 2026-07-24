import { FetchClient, FetchError } from "@intelligent-customer/fetch-client";
import { tokenManager } from "./token-manager";
import { TOKEN_KEY, APP_CONFIG } from "./config";
import { getBusinessErrorType } from "./types";
import { toast } from "sonner";

// 默认实例（客户端），通过请求拦截器注入 token
const fetchClient = new FetchClient({
  baseURL: APP_CONFIG.baseURL,
});

fetchClient.useRequestInterceptor((ctx) => {
  const token = tokenManager.getToken();
  if (token) {
    ctx.config.headers = {
      ...ctx.config.headers,
      Authorization: `Bearer ${token}`,
    };
  }
  return ctx;
});

// 业务错误码 → ErrorType 映射
fetchClient.useResponseErrorInterceptor((error) => {
  if (error instanceof FetchError && error.code) {
    error.type = getBusinessErrorType(error.code);
  }
  return error;
});

fetchClient.useResponseErrorInterceptor((err) => {
  toast.error(err.toString(), { position: "top-center" });
  return err;
});

// ---- re-export 泛型类型 ----
export type {
  ApiResponse,
  FetchRequestConfig,
  HttpMethod,
  UploadProgress,
  FetchInterceptorContext,
} from "@intelligent-customer/fetch-client";

export {
  FetchError,
  ErrorType,
  type RequestInterceptor,
  type ResponseInterceptor,
  type ResponseErrorInterceptor,
} from "@intelligent-customer/fetch-client";

// ---- 业务专属 ----
export { ErrorCode } from "./types";
export {
  HTTP_STATUS,
  PERMISSION_CODE,
  TOKEN_KEY,
  REFRESH_TOKEN_KEY,
} from "./config";

export { InterceptorManager } from "@intelligent-customer/fetch-client";
export { tokenManager } from "./token-manager";
export { FetchClient };

export { fetchClient };
export default fetchClient;

/**
 * 创建服务端 FetchClient 实例，用于 Server Component / Server Action。
 * 通过 `next/headers` 的 cookies() 读取 auth_token。
 */
export async function createServerClient(): Promise<FetchClient> {
  const { cookies } = await import("next/headers");
  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_KEY)?.value ?? null;

  const client = new FetchClient({ baseURL: APP_CONFIG.baseURL });
  if (token) {
    client.setDefaultHeader("Authorization", `Bearer ${token}`);
  }
  return client;
}
