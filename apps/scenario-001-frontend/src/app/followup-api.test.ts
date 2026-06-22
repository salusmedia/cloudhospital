import { describe, it, expect } from "vitest";

import { buildFollowupQuery } from "./followup-api";

describe("buildFollowupQuery", () => {
  it("无参数返回空串", () => {
    expect(buildFollowupQuery()).toBe("");
  });

  it("仅日期", () => {
    expect(buildFollowupQuery("2026-06-01")).toBe("?on=2026-06-01");
  });

  it("日期 + 科室", () => {
    expect(buildFollowupQuery("2026-06-01", "card")).toBe("?on=2026-06-01&dept=card");
  });

  it("第 1 页不带 page 参数", () => {
    expect(buildFollowupQuery(undefined, "card", 1)).toBe("?dept=card");
  });

  it("第 2 页带 page 参数", () => {
    expect(buildFollowupQuery(undefined, undefined, 2)).toBe("?page=2");
  });

  it("特殊字符被正确编码", () => {
    expect(buildFollowupQuery(undefined, "a b&c")).toBe("?dept=a+b%26c");
  });
});
