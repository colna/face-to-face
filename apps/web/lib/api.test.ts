import { afterEach, describe, expect, it, vi } from "vitest";
import { createVideoJob, getJob, listModels, swapImage } from "./api";

function mockFetch(impl: (url: string, init?: RequestInit) => Response) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => impl(url, init));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

const file = (name: string) => new File([new Uint8Array([1, 2, 3])], name);

describe("swapImage", () => {
  it("POST /swap/image 带 FormData,返回 Blob", async () => {
    const fetchFn = mockFetch(
      () => new Response(new Uint8Array([9]).buffer, { status: 200 }),
    );
    const blob = await swapImage(file("s.jpg"), file("t.jpg"), {
      face_enhancer_blend: 70,
      face_selector_mode: "many",
    });
    expect(blob.size).toBe(1);
    expect(Array.from(new Uint8Array(await blob.arrayBuffer()))).toEqual([9]);
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toContain("/swap/image");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeInstanceOf(FormData);
    expect((init?.body as FormData).get("face_enhancer_blend")).toBe("70");
    expect((init?.body as FormData).get("face_selector_mode")).toBe("many");
  });

  it("非 2xx 抛错并带 detail", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ detail: "参数不合法" }), { status: 400 }),
    );
    await expect(swapImage(file("s"), file("t"))).rejects.toThrow("参数不合法");
  });
});

describe("createVideoJob / getJob", () => {
  it("建任务返回 job_id", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ job_id: "abc", status: "pending" }), {
          status: 200,
        }),
    );
    const res = await createVideoJob(file("s"), file("t"), {
      face_selector_mode: "many",
    });
    expect(res.job_id).toBe("abc");
  });

  it("查任务解析 JobState", async () => {
    mockFetch(
      () =>
        new Response(
          JSON.stringify({ id: "abc", status: "done", progress: 1 }),
          { status: 200 },
        ),
    );
    const job = await getJob("abc");
    expect(job.status).toBe("done");
    expect(job.progress).toBe(1);
  });
});

describe("listModels", () => {
  it("返回清单与就绪状态", async () => {
    mockFetch(
      () =>
        new Response(
          JSON.stringify({
            models: [
              { name: "hyperswap", category: "swapper", present: false },
            ],
            all_ready: false,
          }),
          { status: 200 },
        ),
    );
    const res = await listModels();
    expect(res.models[0].name).toBe("hyperswap");
    expect(res.all_ready).toBe(false);
  });
});
