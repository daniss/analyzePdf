import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/lib/auth-context"
import { ReactQueryProvider } from "@/lib/query-client"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "InvoiceAI - Smart Invoice Data Extraction",
  description: "Extract structured data from PDF invoices using AI. Fast, accurate, and reliable invoice processing for modern businesses.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ReactQueryProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  )
}