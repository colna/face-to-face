import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ImageSwap } from "./ImageSwap";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({ swapImage: vi.fn() }));

beforeEach(() => {
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: vi.fn(() => "blob:fake"),
  });
});
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function selectFile(labelText: string, name: string) {
  const input = screen.getByLabelText(labelText) as HTMLInputElement;
  const file = new File([new Uint8Array([1])], name, { type: "image/png" });
  fireEvent.change(input, { target: { files: [file] } });
}

describe("ImageSwap", () => {
  it("按钮初始禁用,选两张图后可点", () => {
    render(<ImageSwap />);
    const btn = screen.getByRole("button", { name: "开始换脸" });
    expect(btn).toBeDisabled();
    selectFile("源脸(Source)", "s.png");
    selectFile("目标图(Target)", "t.png");
    expect(btn).toBeEnabled();
  });

  it("提交调用 swapImage 并展示结果图", async () => {
    vi.mocked(api.swapImage).mockResolvedValue(new Blob([new Uint8Array([9])]));
    render(<ImageSwap />);
    selectFile("源脸(Source)", "s.png");
    selectFile("目标图(Target)", "t.png");
    fireEvent.click(screen.getByRole("button", { name: "开始换脸" }));
    await waitFor(() =>
      expect(screen.getByAltText("换脸结果")).toBeInTheDocument(),
    );
    expect(api.swapImage).toHaveBeenCalledOnce();
    const params = vi.mocked(api.swapImage).mock.calls[0][2];
    expect(params).toMatchObject({
      face_enhancer: "codeformer",
      face_enhancer_blend: 80,
      occlusion_mask: true,
    });
  });

  it("失败展示错误", async () => {
    vi.mocked(api.swapImage).mockRejectedValue(new Error("引擎炸了"));
    render(<ImageSwap />);
    selectFile("源脸(Source)", "s.png");
    selectFile("目标图(Target)", "t.png");
    fireEvent.click(screen.getByRole("button", { name: "开始换脸" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("引擎炸了"),
    );
  });
});
