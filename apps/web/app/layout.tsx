import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FaceForge",
  description: "自建 · 质量优先的 AI 换脸平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
