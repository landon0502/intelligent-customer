import type {
  FetchInterceptorContext,
  RequestInterceptor,
  ResponseErrorInterceptor,
  ResponseInterceptor,
} from "./types"

export class InterceptorManager {
  private requestInterceptors: RequestInterceptor[] = []
  private responseInterceptors: ResponseInterceptor[] = []
  private responseErrorInterceptors: ResponseErrorInterceptor[] = []

  useRequest(interceptor: RequestInterceptor): () => void {
    this.requestInterceptors.push(interceptor)
    return () => this.remove(this.requestInterceptors, interceptor)
  }

  useResponse(interceptor: ResponseInterceptor): () => void {
    this.responseInterceptors.push(interceptor)
    return () => this.remove(this.responseInterceptors, interceptor)
  }

  useResponseError(interceptor: ResponseErrorInterceptor): () => void {
    this.responseErrorInterceptors.push(interceptor)
    return () => this.remove(this.responseErrorInterceptors, interceptor)
  }

  async runRequest(
    ctx: FetchInterceptorContext
  ): Promise<FetchInterceptorContext> {
    let result = ctx
    for (const interceptor of this.requestInterceptors) {
      result = await interceptor(result)
    }
    return result
  }

  async runResponse(
    response: Response,
    ctx: FetchInterceptorContext
  ): Promise<Response> {
    let result = response
    for (const interceptor of this.responseInterceptors) {
      result = await interceptor(result, ctx)
    }
    return result
  }

  async runResponseError(
    error: Error,
    ctx: FetchInterceptorContext
  ): Promise<Error> {
    let result = error
    for (const interceptor of this.responseErrorInterceptors) {
      result = await interceptor(result, ctx)
    }
    return result
  }

  private remove<T>(list: T[], item: T): void {
    const idx = list.indexOf(item)
    if (idx >= 0) list.splice(idx, 1)
  }
}
