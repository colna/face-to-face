import Link from "next/link";

const links = [
  { href: "/image", label: "图片" },
  { href: "/video", label: "视频" },
  { href: "/realtime", label: "实时" },
];

export function NavBar() {
  return (
    <header
      className="sticky top-0 z-10 border-b backdrop-blur"
      style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--bg) 80%, transparent)" }}
    >
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          FaceForge
        </Link>
        <ul className="flex gap-6 text-sm" style={{ color: "var(--muted)" }}>
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="transition-colors hover:text-[color:var(--fg)]">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
