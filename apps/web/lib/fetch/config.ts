export { HTTP_STATUS, DEFAULT_CONFIG } from "@intelligent-customer/fetch-client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL! + process.env.NEXT_PUBLIC_API_BASE_URL;

export const TOKEN_KEY = "auth_token";
export const REFRESH_TOKEN_KEY = "refresh_token";

export const APP_CONFIG = {
  baseURL: BASE_URL,
};

export const PERMISSION_CODE = {
  LOGIN: "user:login",
  LOGOUT: "user:logout",
  READ: "data:read",
  WRITE: "data:write",
  DELETE: "data:delete",
  ADMIN: "admin:*",
} as const;
