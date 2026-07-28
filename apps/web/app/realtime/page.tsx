import { RealtimeSwap } from "@/components/RealtimeSwap";

export default function RealtimePage() {
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-bold">实时换脸</h1>
      <RealtimeSwap />
    </main>
  );
}
