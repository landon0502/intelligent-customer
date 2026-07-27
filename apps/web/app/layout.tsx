import localFont from "next/font/local"

import "@intelligent-customer/ui/globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@intelligent-customer/ui/lib/utils";

const geist = localFont({
  src: "../fonts/geist-latin.woff2",
  variable: "--font-sans",
  weight: "100 900",
})

const fontMono = localFont({
  src: "../fonts/geist-mono-latin.woff2",
  variable: "--font-mono",
  weight: "100 900",
})

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("antialiased", fontMono.variable, "font-sans", geist.variable)}
    >
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  )
}
