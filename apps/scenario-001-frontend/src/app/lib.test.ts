import { describe, it, expect } from "vitest";
import { greeting } from "./lib";

describe("scenario-001 frontend", () => {
  it("greeting 拼接名称", () => {
    expect(greeting("随访")).toBe("欢迎使用 随访");
  });
});
