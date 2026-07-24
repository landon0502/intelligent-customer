export {
  FetchError,
  ErrorType,
  getErrorType,
  type ApiResponse,
  type FetchRequestConfig,
  type HttpMethod,
  type UploadProgress,
  type FetchInterceptorContext,
  type RequestInterceptor,
  type ResponseInterceptor,
  type ResponseErrorInterceptor,
} from "@intelligent-customer/fetch-client";

import { ErrorType } from "@intelligent-customer/fetch-client";

/** 业务错误码 → ErrorType 映射，替换 packages 中的通用 getErrorType */
export function getBusinessErrorType(code: number): ErrorType {
  if (code === 0) return ErrorType.UnknownError;

  if (code >= 10001 && code <= 10006) {
    if (code === 10005) return ErrorType.RateLimitError;
    if (code >= 10001 && code <= 10003) return ErrorType.ValidationError;
    return ErrorType.ServerError;
  }

  if (code >= 20001 && code <= 20006) {
    if (code === 20002) return ErrorType.TokenExpired;
    if (code === 20004) return ErrorType.TokenReplaced;
    if (code === 20005) return ErrorType.PermissionError;
    if (code === 20006) return ErrorType.AccountFrozen;
    return ErrorType.AuthError;
  }

  if (code >= 30001 && code <= 30005) return ErrorType.ValidationError;

  if (code >= 40001 && code <= 40004) {
    if (code === 40001) return ErrorType.NotFoundError;
    if (code === 40003) return ErrorType.ConflictError;
    return ErrorType.ServerError;
  }

  if (code >= 50001 && code <= 50004) return ErrorType.ServerError;

  return ErrorType.UnknownError;
}

// 业务错误码（ling-diary 项目专属）
export const ErrorCode = {
  SUCCESS: 0,
  PARAM_FORMAT_ERROR: 10001,
  MISSING_PARAM: 10002,
  PARAM_TYPE_ERROR: 10003,
  INTERFACE_OFFLINE: 10004,
  RATE_LIMIT_EXCEEDED: 10005,
  SYSTEM_INTERNAL_ERROR: 10006,
  NO_AUTH_TOKEN: 20001,
  TOKEN_EXPIRED: 20002,
  TOKEN_INVALID: 20003,
  TOKEN_REPLACED: 20004,
  PERMISSION_DENIED: 20005,
  ACCOUNT_FROZEN: 20006,
  INVALID_CREDENTIALS: 30001,
  USER_ALREADY_EXISTS: 30002,
  USER_NOT_FOUND: 30003,
  VERIFY_CODE_INVALID: 30004,
  SAME_PASSWORD: 30005,
  RESOURCE_NOT_FOUND: 40001,
  RESOURCE_STATUS_INVALID: 40002,
  DATA_CONFLICT: 40003,
  DATA_WRITE_FAILED: 40004,
  FILE_UPLOAD_FAILED: 50001,
  PAYMENT_TIMEOUT: 50002,
  SMS_SEND_FAILED: 50003,
  REMOTE_SERVICE_UNAVAILABLE: 50004,
} as const;
