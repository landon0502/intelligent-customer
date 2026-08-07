import { AppLayout } from "@/components/layout/app-layout"
import { AuthGuard } from "@/components/auth-guard"

export default function DiaryLayout({
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
