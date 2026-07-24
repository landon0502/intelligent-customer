import { DEFAULT_CONFIG, HTTP_STATUS, SUCCESS_CODE } from "./config";
import { InterceptorManager } from "./interceptor-manager";
import {
  ErrorType,
  FetchError,
  getErrorType,
  type ApiResponse,
  type FetchClientOptions,
  type FetchInterceptorContext,
  type FetchRequestConfig,
  type HttpMethod,
  type RequestInterceptor,
  type ResponseErrorInterceptor,
  type ResponseInterceptor,
  type UploadProgress,
} from "./types";

// ==================== 工具函数 ====================

function buildURL(
  baseURL: string,
  url: string,
  params?: Record<string, unknown>
): string {
  const fullURL = url.startsWith("http") ? url : `${baseURL}${url}`;
  if (!params) return fullURL;

  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  const qs = searchParams.toString();
  if (!qs) return fullURL;
  return `${fullURL}${fullURL.includes("?") ? "&" : "?"}${qs}`;
}

function getRetryDelay(config: FetchRequestConfig, attempt: number): number {
  const raw = config.retryDelay ?? DEFAULT_CONFIG.retryDelay;
  if (typeof raw === "function") return raw(attempt);
  return raw;
}

// ==================== FetchClient ====================

export class FetchClient {
  private baseURL: string;
  private defaultConfig: FetchRequestConfig;
  private interceptors = new InterceptorManager();

  private pendingMap = new Map<string, Promise<unknown>>();

  constructor(options?: FetchClientOptions) {
    this.baseURL = options?.baseURL ?? DEFAULT_CONFIG.baseURL;
    this.defaultConfig = { ...DEFAULT_CONFIG, ...options };
  }

  // ==================== 拦截器注册 ====================

  useRequestInterceptor(interceptor: RequestInterceptor): () => void {
    return this.interceptors.useRequest(interceptor);
  }

  useResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    return this.interceptors.useResponse(interceptor);
  }

  useResponseErrorInterceptor(
    interceptor: ResponseErrorInterceptor
  ): () => void {
    return this.interceptors.useResponseError(interceptor);
  }

  // ==================== 配置方法 ====================

  setBaseURL(url: string): void {
    this.baseURL = url;
  }

  setDefaultHeader(key: string, value: string): void {
    this.defaultConfig.headers = {
      ...this.defaultConfig.headers,
      [key]: value,
    };
  }

  removeDefaultHeader(key: string): void {
    if (!this.defaultConfig.headers) return;
    const { [key]: _, ...rest } = this.defaultConfig.headers;
    this.defaultConfig.headers = rest;
  }

  // ==================== 核心请求方法 ====================

  async request<T = unknown>(
    url: string,
    method: HttpMethod = "GET",
    body?: unknown,
    config?: FetchRequestConfig
  ): Promise<ApiResponse<T>> {
    const mergedConfig: FetchRequestConfig = {
      ...this.defaultConfig,
      ...config,
      headers: {
        ...this.defaultConfig.headers,
        ...config?.headers,
      } as Record<string, string>,
    };

    const ctx = await this.interceptors.runRequest({
      url,
      method,
      config: mergedConfig,
      body,
    });
    const finalURL = buildURL(this.baseURL, ctx.url, ctx.config.params);
    const maxRetry = ctx.config.retry ?? 0;
    let lastError: Error | null = null;

    try {
      for (let attempt = 0; attempt <= maxRetry; attempt++) {
        try {
          return await this._doRequest<T>(
            finalURL,
            ctx.method,
            ctx.body,
            ctx.config
          );
        } catch (err) {
          lastError = err as Error;

          if (err instanceof FetchError) {
            const shouldRetry =
              attempt < maxRetry &&
              (err.type === ErrorType.NetworkError ||
                err.type === ErrorType.TimeoutError ||
                err.type === ErrorType.ServerError);
            if (!shouldRetry) throw err;
          } else if (err instanceof DOMException && err.name === "AbortError") {
            throw new FetchError("请求已取消", ErrorType.Cancelled);
          } else if (attempt >= maxRetry) {
            throw err;
          }

          const delay = getRetryDelay(ctx.config, attempt + 1);
          await new Promise((r) => setTimeout(r, delay));
        }
      }
      throw lastError!;
    } catch (err) {
      if (!ctx.config.skipErrorHandler && err instanceof Error) {
        const processed = await this.interceptors.runResponseError(err, ctx);
        throw processed;
      }
      throw err;
    }
  }

  private async _doRequest<T>(
    url: string,
    method: HttpMethod,
    body: unknown,
    config: FetchRequestConfig
  ): Promise<ApiResponse<T>> {
    const headers = new Headers(config.headers);

    let processedBody: BodyInit | undefined;
    if (body !== undefined && body !== null) {
      if (body instanceof FormData) {
        processedBody = body;
        headers.delete("Content-Type");
      } else if (typeof body === "string") {
        processedBody = body;
      } else if (body instanceof Blob) {
        processedBody = body;
      } else if (body instanceof ArrayBuffer || ArrayBuffer.isView(body)) {
        processedBody = new Blob([body as ArrayBuffer]);
      } else if (body instanceof URLSearchParams) {
        processedBody = body;
      } else {
        processedBody = JSON.stringify(body);
        if (!headers.has("Content-Type"))
          headers.set("Content-Type", "application/json");
      }
    }

    const ctx: FetchInterceptorContext = { url, method, config, body };

    const controller = new AbortController();
    const timeoutMs = config.timeout ?? DEFAULT_CONFIG.timeout;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    if (config.signal) {
      if (config.signal.aborted) {
        clearTimeout(timeoutId);
        throw new FetchError("请求已取消", ErrorType.Cancelled);
      }
      config.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: ["GET", "HEAD"].includes(method) ? undefined : processedBody,
        signal: controller.signal,
        cache: config.cache,
        credentials: config.credentials,
      });
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof DOMException && err.name === "AbortError") {
        if (config.signal?.aborted)
          throw new FetchError("请求已取消", ErrorType.Cancelled);
        throw new FetchError("请求超时", ErrorType.TimeoutError);
      }
      throw new FetchError("网络错误，请检查网络连接", ErrorType.NetworkError);
    } finally {
      clearTimeout(timeoutId);
    }

    response = await this.interceptors.runResponse(response, ctx);

    if (!response.ok) await this._handleHttpError(response);
    return this._parseResponse<T>(response, config);
  }

  // ==================== HTTP 错误处理 ====================

  private async _handleHttpError(
    response: Response
  ): Promise<never> {
    const { status } = response;

    if (status === HTTP_STATUS.UNAUTHORIZED) {
      throw new FetchError("未授权", ErrorType.AuthError, { status });
    }
    if (status === HTTP_STATUS.FORBIDDEN) {
      throw new FetchError("禁止访问", ErrorType.PermissionError, { status });
    }
    if (status === HTTP_STATUS.NOT_FOUND) {
      throw new FetchError("资源不存在", ErrorType.NotFoundError, { status });
    }
    if (status === HTTP_STATUS.TOO_MANY_REQUESTS) {
      throw new FetchError("请求过频", ErrorType.RateLimitError, { status });
    }
    if (status >= 500) {
      throw new FetchError("服务器错误", ErrorType.ServerError, { status });
    }

    throw new FetchError("请求失败", ErrorType.UnknownError, { status });
  }

  // ==================== 响应解析 ====================

  private async _parseResponse<T>(
    response: Response,
    config: FetchRequestConfig
  ): Promise<ApiResponse<T>> {
    const responseType = config.responseType ?? "json";

    if (response.status === HTTP_STATUS.NO_CONTENT) {
      return { code: 0, message: "success", data: undefined as unknown as T };
    }
    if (responseType === "blob") {
      return {
        code: 0,
        message: "success",
        data: (await response.blob()) as unknown as T,
      };
    }
    if (responseType === "arrayBuffer") {
      return {
        code: 0,
        message: "success",
        data: (await response.arrayBuffer()) as unknown as T,
      };
    }
    if (responseType === "text") {
      return {
        code: 0,
        message: "success",
        data: (await response.text()) as unknown as T,
      };
    }

    const json: ApiResponse<T> = await response.json();
    if (json.code !== undefined && json.code !== SUCCESS_CODE) {
      throw new FetchError(
        json.message || "请求失败",
        getErrorType(json.code),
        {
          code: json.code,
          status: response.status,
          response: json,
        }
      );
    }
    return json;
  }

  // ==================== 便捷方法 ====================

  get<T = unknown>(
    url: string,
    params?: Record<string, unknown>,
    config?: FetchRequestConfig
  ) {
    return this.request<T>(url, "GET", undefined, { ...config, params });
  }

  post<T = unknown>(url: string, body?: unknown, config?: FetchRequestConfig) {
    return this.request<T>(url, "POST", body, config);
  }

  put<T = unknown>(url: string, body?: unknown, config?: FetchRequestConfig) {
    return this.request<T>(url, "PUT", body, config);
  }

  patch<T = unknown>(url: string, body?: unknown, config?: FetchRequestConfig) {
    return this.request<T>(url, "PATCH", body, config);
  }

  delete<T = unknown>(
    url: string,
    params?: Record<string, unknown>,
    config?: FetchRequestConfig
  ) {
    return this.request<T>(url, "DELETE", undefined, { ...config, params });
  }

  // ==================== 文件上传 ====================

  async upload<T = unknown>(
    url: string,
    formData: FormData,
    onProgress?: (progress: UploadProgress) => void,
    config?: FetchRequestConfig
  ): Promise<ApiResponse<T>> {
    if (onProgress && typeof XMLHttpRequest !== "undefined") {
      return this._uploadWithProgress<T>(url, formData, onProgress, config);
    }
    return this.request<T>(url, "POST", formData, config);
  }

  private async _uploadWithProgress<T>(
    url: string,
    formData: FormData,
    onProgress: (progress: UploadProgress) => void,
    config?: FetchRequestConfig
  ): Promise<ApiResponse<T>> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fullURL = buildURL(this.baseURL, url);
      xhr.open("POST", fullURL);
      xhr.timeout = config?.timeout ?? DEFAULT_CONFIG.timeout;

      if (config?.headers) {
        Object.entries(config.headers).forEach(([key, value]) => {
          if (key.toLowerCase() !== "content-type")
            xhr.setRequestHeader(key, value);
        });
      }

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress({
            loaded: e.loaded,
            total: e.total,
            percent: Math.round((e.loaded / e.total) * 100),
          });
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const json = JSON.parse(xhr.responseText);
            if (json.code !== undefined && json.code !== SUCCESS_CODE) {
              reject(
                new FetchError(
                  json.message || "上传失败",
                  getErrorType(json.code),
                  { code: json.code, status: xhr.status }
                )
              );
            } else {
              resolve(json);
            }
          } catch {
            resolve({
              code: 0,
              message: "success",
              data: xhr.responseText as unknown as T,
            });
          }
        } else if (xhr.status === HTTP_STATUS.UNAUTHORIZED) {
          reject(
            new FetchError("未授权", ErrorType.AuthError, {
              status: xhr.status,
            })
          );
        } else {
          reject(
            new FetchError("上传失败", ErrorType.ServerError, {
              status: xhr.status,
            })
          );
        }
      });

      xhr.addEventListener("error", () =>
        reject(new FetchError("网络错误", ErrorType.NetworkError))
      );
      xhr.addEventListener("timeout", () =>
        reject(new FetchError("上传超时", ErrorType.TimeoutError))
      );
      xhr.addEventListener("abort", () =>
        reject(new FetchError("上传已取消", ErrorType.Cancelled))
      );
      xhr.send(formData);
    });
  }

  // ==================== 文件下载 ====================

  async download(
    url: string,
    fileName?: string,
    config?: FetchRequestConfig
  ): Promise<void> {
    const response = await this.request<Blob>(url, "GET", undefined, {
      ...config,
      responseType: "blob",
    });
    const blob = response.data as unknown as Blob;
    const objectURL = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectURL;
    link.download = fileName || "download";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectURL);
  }

  // ==================== SSE ====================

  async sse(
    url: string,
    onMessage: (data: string, event: string) => void,
    config?: FetchRequestConfig
  ): Promise<() => void> {
    const controller = new AbortController();
    const fullURL = buildURL(this.baseURL, url, config?.params);
    const headers = new Headers(config?.headers);

    const response = await fetch(fullURL, {
      headers,
      signal: controller.signal,
      credentials: config?.credentials,
    });

    if (!response.ok || !response.body)
      throw new FetchError("SSE 连接失败", ErrorType.ServerError);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const read = () => {
      reader
        .read()
        .then(({ done, value }) => {
          if (done) return;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          let currentEvent = "message";
          let currentData = "";
          for (const line of lines) {
            if (line.startsWith("event:")) currentEvent = line.slice(6).trim();
            else if (line.startsWith("data:"))
              currentData += line.slice(5).trim();
            else if (line === "" && currentData) {
              onMessage(currentData, currentEvent);
              currentData = "";
              currentEvent = "message";
            }
          }
          read();
        })
        .catch(() => {
          /* stream closed */
        });
    };

    read();
    return () => {
      controller.abort();
      reader.cancel();
    };
  }

  // ==================== 请求去重 ====================

  async dedupedRequest<T>(
    key: string,
    factory: () => Promise<ApiResponse<T>>
  ): Promise<ApiResponse<T>> {
    if (this.pendingMap.has(key))
      return this.pendingMap.get(key) as Promise<ApiResponse<T>>;
    const promise = factory().finally(() => {
      this.pendingMap.delete(key);
    });
    this.pendingMap.set(key, promise);
    return promise;
  }

  clearPending(): void {
    this.pendingMap.clear();
  }
}
