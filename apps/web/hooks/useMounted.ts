"use client"
import { useSyncExternalStore } from "react"
export function useMounted() {
  const emptySubscribe = () => () => {}
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  )

  return mounted
}
