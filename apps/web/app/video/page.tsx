import { VideoSwap } from "@/components/VideoSwap";

export default function VideoPage() {
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-bold">视频换脸</h1>
      <VideoSwap />
    </main>
  );
}
