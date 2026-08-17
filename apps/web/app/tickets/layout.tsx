import { AppLayout } from "@/components/layout/app-layout"
import { AuthGuard } from "@/components/auth-guard"

export default function TicketsLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthGuard>
      <AppLayout>{children}</AppLayout>
    </AuthGuard>
  )
}
