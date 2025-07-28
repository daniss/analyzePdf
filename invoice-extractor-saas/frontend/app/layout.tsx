import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/lib/auth-context"
import { ReactQueryProvider } from "@/lib/query-client"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "FacturePro - Extraction Intelligente de Données",
  description: "Extraction de données structurées à partir de factures PDF. Traitement rapide, précis et fiable pour les entreprises modernes.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="fr">
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