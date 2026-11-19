import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";

export const metadata: Metadata = {
  title: "VoiceRag — Multilingual AI Voice & Knowledge Platform",
  description: "Enterprise Multilingual AI Voice and Knowledge Assistant with Hybrid RAG and Real-time Voice (English + Arabic)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
