import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VideoSwap } from "./VideoSwap";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  createVideoJob: vi.fn(),
  getJob: vi.fn(),
  downloadJob: vi.fn(),
}));

beforeEach(() => {
  vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:fake") });
});
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function selectFile(labelText: string, name: string, type: string) {
  const input = screen.getByLabelText(labelText) as HTMLInputElement;
  fireEvent.change(input, {
    target: { files: [new File([new Uint8Array([1])], name, { type })] },
  });
}

function pickBoth() {
  selectFile("源脸(Source)", "s.png", "image/png");
  selectFile("目标视频(Target)", "t.mp4", "video/mp4");
}

describe("VideoSwap", () => {
  it("建任务→轮询到 done→出现下载按钮", async () => {
    vi.mocked(api.createVideoJob).mockResolvedValue({
      job_id: "j1",
      status: "pending",
    });
    vi.mocked(api.getJob)
      .mockResolvedValueOnce({ id: "j1", status: "running", progress: 0.5 })
      .mockResolvedValueOnce({ id: "j1", status: "done", progress: 1 });
    render(<VideoSwap pollMs={1} />);
    pickBoth();
    fireEvent.click(screen.getByRole("button", { name: "开始换脸" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "下载结果" }),
      ).toBeInTheDocument(),
    );
    expect(api.createVideoJob).toHaveBeenCalledOnce();
    expect(vi.mocked(api.createVideoJob).mock.calls[0][2]).toEqual({
      occlusion_mask: false,
      face_selector_mode: "many",
    });
  });

  it("任务 failed 展示错误", async () => {
    vi.mocked(api.createVideoJob).mockResolvedValue({
      job_id: "j2",
      status: "pending",
    });
    vi.mocked(api.getJob).mockResolvedValue({
      id: "j2",
      status: "failed",
      progress: 0,
      error: "转码失败",
    });
    render(<VideoSwap pollMs={1} />);
    pickBoth();
    fireEvent.change(screen.getByLabelText("换脸范围"), {
      target: { value: "one" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始换脸" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("转码失败"),
    );
    expect(vi.mocked(api.createVideoJob).mock.calls[0][2]).toEqual({
      occlusion_mask: false,
      face_selector_mode: "one",
    });
  });

  it("点下载调用 downloadJob", async () => {
    vi.mocked(api.createVideoJob).mockResolvedValue({
      job_id: "j3",
      status: "pending",
    });
    vi.mocked(api.getJob).mockResolvedValue({
      id: "j3",
      status: "done",
      progress: 1,
    });
    vi.mocked(api.downloadJob).mockResolvedValue(
      new Blob([new Uint8Array([1])]),
    );
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<VideoSwap pollMs={1} />);
    pickBoth();
    fireEvent.click(screen.getByRole("button", { name: "开始换脸" }));
    const dl = await screen.findByRole("button", { name: "下载结果" });
    fireEvent.click(dl);
    await waitFor(() => expect(api.downloadJob).toHaveBeenCalledWith("j3"));
  });
});
