import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeSwap } from "./RealtimeSwap";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({ connectRealtime: vi.fn() }));

const getUserMedia = vi.fn();
const trackStop = vi.fn();
const close = vi.fn();

beforeEach(() => {
  getUserMedia.mockResolvedValue({ getTracks: () => [{ stop: trackStop }] });
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  vi.mocked(api.connectRealtime).mockReturnValue({ sendFrame: vi.fn(), close });
});
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("RealtimeSwap", () => {
  it("无 source 时开始按钮禁用", () => {
    render(<RealtimeSwap />);
    expect(screen.getByRole("button", { name: "开始" })).toBeDisabled();
  });

  it("开始:强制前置摄像头 + 建立 WS", async () => {
    render(<RealtimeSwap />);
    fireEvent.change(screen.getByPlaceholderText("/faces/a.jpg"), {
      target: { value: "/faces/a.jpg" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "停止" })).toBeInTheDocument(),
    );
    expect(getUserMedia).toHaveBeenCalledWith({
      video: { facingMode: "user" },
      audio: false,
    });
    expect(api.connectRealtime).toHaveBeenCalledWith(
      "/faces/a.jpg",
      expect.any(Function),
      expect.any(Function),
    );
  });

  it("停止:关闭 WS 与摄像头轨道", async () => {
    render(<RealtimeSwap />);
    fireEvent.change(screen.getByPlaceholderText("/faces/a.jpg"), {
      target: { value: "/faces/a.jpg" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始" }));
    const stopBtn = await screen.findByRole("button", { name: "停止" });
    fireEvent.click(stopBtn);
    expect(close).toHaveBeenCalled();
    expect(trackStop).toHaveBeenCalled();
  });
});
