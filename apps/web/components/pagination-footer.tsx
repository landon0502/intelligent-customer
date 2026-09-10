"use client"

import { useTranslations } from "next-intl"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@intelligent-customer/ui/components/pagination"

/** 生成页码列表；总页数超过 7 时折叠中间部分为省略号 */
export function getPageItems(
  current: number,
  totalPages: number
): (number | "ellipsis")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }
  const start = Math.max(2, current - 1)
  const end = Math.min(totalPages - 1, current + 1)
  const items: (number | "ellipsis")[] = [1]
  if (start > 2) items.push("ellipsis")
  for (let p = start; p <= end; p++) items.push(p)
  if (end < totalPages - 1) items.push("ellipsis")
  items.push(totalPages)
  return items
}

interface PaginationFooterProps {
  /** 当前页，从 1 开始 */
  page: number
  /** 总页数；<= 1 时不渲染 */
  totalPages: number
  onPageChange: (page: number) => void
}

/**
 * 表格底部分页条 —— 左侧页码信息，右侧分页控件。
 * 越界与同页点击由组件内部拦截，调用方直接传 setPage 即可。
 */
export function PaginationFooter({
  page,
  totalPages,
  onPageChange,
}: PaginationFooterProps) {
  const t = useTranslations("common")

  if (totalPages <= 1) return null

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3">
      <p className="text-sm text-muted-foreground">
        {t("pageInfo", { page, totalPages })}
      </p>
      <Pagination className="mx-0 w-auto justify-end">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              href="#"
              text={t("prevPage")}
              aria-disabled={page <= 1}
              className={page <= 1 ? "pointer-events-none opacity-50" : undefined}
              onClick={(e) => {
                e.preventDefault()
                if (page > 1) onPageChange(page - 1)
              }}
            />
          </PaginationItem>
          {getPageItems(page, totalPages).map((item, i) =>
            item === "ellipsis" ? (
              <PaginationItem key={`ellipsis-${i}`}>
                <PaginationEllipsis />
              </PaginationItem>
            ) : (
              <PaginationItem key={item}>
                <PaginationLink
                  href="#"
                  isActive={item === page}
                  onClick={(e) => {
                    e.preventDefault()
                    if (item !== page) onPageChange(item)
                  }}
                >
                  {item}
                </PaginationLink>
              </PaginationItem>
            )
          )}
          <PaginationItem>
            <PaginationNext
              href="#"
              text={t("nextPage")}
              aria-disabled={page >= totalPages}
              className={
                page >= totalPages
                  ? "pointer-events-none opacity-50"
                  : undefined
              }
              onClick={(e) => {
                e.preventDefault()
                if (page < totalPages) onPageChange(page + 1)
              }}
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  )
}
