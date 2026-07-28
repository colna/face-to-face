import { render, screen } from "@testing-library/react";
import Home from "./page";

test("首页渲染 FaceForge 标题", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { name: "FaceForge" })).toBeInTheDocument();
});
