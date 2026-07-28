import { ImageSwap } from "@/components/ImageSwap";

export default function ImagePage() {
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-bold">图片换脸</h1>
      <ImageSwap />
    </main>
  );
}
