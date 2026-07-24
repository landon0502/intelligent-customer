// ==================== 基础响应 ====================

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// ==================== 请求配置 ====================

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD";

export interface FetchRequestConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
  retry?: number;
  retryDelay?: number | ((attempt: number) => number);
  skipErrorHandler?: boolean;
  responseType?: "json" | "text" | "blob" | "arrayBuffer";
  signal?: AbortSignal;
  cache?: RequestCache;
  credentials?: RequestCredentials;
  dedupeKey?: string;
  params?: Record<string, unknown>;
}

// ==================== 错误类型 ====================

export enum ErrorType {
  NetworkError = "NetworkError",
  TimeoutError = "TimeoutError",
  AuthError = "AuthError",
  TokenExpired = "TokenExpired",
  TokenReplaced = "TokenReplaced",
  PermissionError = "PermissionError",
  AccountFrozen = "AccountFrozen",
  ValidationError = "ValidationError",
  NotFoundError = "NotFoundError",
  ConflictError = "ConflictError",
  RateLimitError = "RateLimitError",
  ServerError = "ServerError",
  UnknownError = "UnknownError",
  Cancelled = "Cancelled",
}

export class FetchError extends Error {
  type: ErrorType;
  code?: number;
  status?: number;
  response?: unknown;

  constructor(
    message: string,
    type: ErrorType,
    opts?: { code?: number; status?: number; response?: unknown }
  ) {
    super(message);
    this.name = "FetchError";
    this.type = type;
    this.code = opts?.code;
    this.status = opts?.status;
    this.response = opts?.response;
  }
}

/** 通用错误码映射，业务方可通过拦截器替换为自定义逻辑 */
export function getErrorType(code: number): ErrorType {
  if (code === 0) return ErrorType.UnknownError;
  return ErrorType.ServerError;
}

// ==================== 拦截器 ====================

export interface FetchInterceptorContext {
  url: string;
  method: HttpMethod;
  config: FetchRequestConfig;
  body?: unknown;
}

export type RequestInterceptor = (
  ctx: FetchInterceptorContext
) => FetchInterceptorContext | Promise<FetchInterceptorContext>;

export type ResponseInterceptor = (
  response: Response,
  ctx: FetchInterceptorContext
) => Response | Promise<Response>;

export type ResponseErrorInterceptor = (
  error: Error,
  ctx: FetchInterceptorContext
) => Error | Promise<Error>;

// ==================== 进度回调 ====================

export interface UploadProgress {
  loaded: number;
  total: number;
  percent: number;
}

export interface FetchClientOptions extends FetchRequestConfig {}
