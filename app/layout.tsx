import type React from "react"
import type { Metadata } from "next"
import "./globals.css"
import { Footer } from "@/components/Footer"

export const metadata: Metadata = {
  title: "Machine 3.0",
  description: "Created with v0",
  generator: "v0.dev",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="flex flex-col min-h-screen">
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  )
}
