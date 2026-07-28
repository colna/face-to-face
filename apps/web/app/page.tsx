import Link from "next/link";

const tools = [
  { href: "/image", title: "图片换脸", desc: "上传源脸与目标图,质量优先出图。" },
  { href: "/video", title: "视频换脸", desc: "逐帧换脸 + 增强,异步任务带进度。" },
  { href: "/realtime", title: "实时换脸", desc: "前置摄像头,低延迟逐帧换脸。" },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6">
      <section className="flex flex-col items-center gap-4 py-20 text-center">
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">FaceForge</h1>
        <p className="max-w-xl text-lg" style={{ color: "var(--muted)" }}>
          自建 · 质量优先的 AI 换脸平台。图片、视频、实时,一套系统搞定,数据不出本机。
        </p>
      </section>

      <section className="grid gap-5 pb-20 sm:grid-cols-3">
        {tools.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="group flex flex-col gap-2 rounded-2xl border p-6 transition-transform hover:-translate-y-1"
            style={{ borderColor: "var(--border)", background: "var(--card)" }}
          >
            <h2 className="text-xl font-semibold">{t.title}</h2>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {t.desc}
            </p>
            <span className="mt-2 text-sm text-[#0071e3]">进入 →</span>
          </Link>
        ))}
      </section>
    </main>
  );
}
