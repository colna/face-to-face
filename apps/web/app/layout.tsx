import type { Metadata } from "next";
import { NavBar } from "@/components/NavBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "FaceForge · 自建 AI 换脸平台",
  description: "自建 · 质量优先的 AI 换脸平台:图片 / 视频 / 实时,数据不出本机。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <NavBar />
        {children}
        <footer
          className="mx-auto max-w-5xl px-6 py-10 text-xs"
          style={{ color: "var(--muted)" }}
        >
          仅限已获知情同意的素材;不用于冒充、诈骗或非自愿影像。产物默认带溯源水印。
        </footer>
      </body>
    </html>
  );
}
