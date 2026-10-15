import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { ToastProvider } from "@/components/ui/toast";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export const metadata: Metadata = {
  title: "DocGuard AI — Procurement Compliance",
  description: "AI-powered procurement compliance and audit reviewer",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full" style={{ background: "var(--bg-page)", color: "var(--text-primary)" }}>
        <Providers>
          <ToastProvider>
            <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
              <Sidebar />
              <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
                <Header />
                <main style={{ flex: 1, overflowY: "auto", padding: "28px 32px", background: "var(--bg-page)" }}>
                  <div style={{ maxWidth: 1440, margin: "0 auto", width: "100%" }}>
                    {children}
                  </div>
                </main>
              </div>
            </div>
          </ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
