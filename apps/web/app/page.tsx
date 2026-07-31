"use client"

import { useEffect } from "react"
import { Spinner } from "@intelligent-customer/ui/components/spinner"
export default function HomePage() {
  useEffect(() => {
    window.location.href = "/chat"
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="relative text-center">
        <Spinner></Spinner>
      </div>
    </div>
  )
}
