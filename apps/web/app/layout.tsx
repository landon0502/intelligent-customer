import localFont from "next/font/local"
import { getLocale, getMessages } from "next-intl/server"
import { NextIntlClientProvider } from "next-intl"
import { Toaster } from "sonner"
import "@intelligent-customer/ui/globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@intelligent-customer/ui/lib/utils"

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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const locale = await getLocale()
  const messages = await getMessages()

  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={cn(
        "antialiased",
        fontMono.variable,
        "font-sans",
        geist.variable
      )}
    >
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider>
            <Toaster />
            {children}
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
