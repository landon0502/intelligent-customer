export interface FetchPaginationParams {
  page: number
  pageSize: number
  keyword?: string
}

/** 对应后端 schemas/common.py 的 PageResult */
export interface PaginationResponse<T> {
  list: Array<T>
  total: number
  page: number
  page_size: number
}
