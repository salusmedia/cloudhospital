import { describe, expect, it } from "vitest";

import { extractToken } from "./AuthGate";

describe("extractToken", () => {
  it("从登录响应取出顶层 token", () => {
    expect(extractToken({ token: "abc", name: "李医生" })).toBe("abc");
  });

  it("无 token 字段返回 null", () => {
    expect(extractToken({ name: "x" })).toBeNull();
  });

  it("token 非字符串/为空返回 null", () => {
    expect(extractToken({ token: 123 })).toBeNull();
    expect(extractToken({ token: "" })).toBeNull();
  });

  it("非对象返回 null", () => {
    expect(extractToken(null)).toBeNull();
    expect(extractToken("token")).toBeNull();
    expect(extractToken(undefined)).toBeNull();
  });
});
