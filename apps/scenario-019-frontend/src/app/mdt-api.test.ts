import { describe, expect, it } from "vitest";

import { parseExperts } from "./mdt-api";

describe("parseExperts", () => {
  it("解析多行 姓名,科室,机构", () => {
    const out = parseExperts("张主任,心内科,温州市中心医院\n李医生,影像科");
    expect(out).toEqual([
      { name: "张主任", dept: "心内科", org: "温州市中心医院" },
      { name: "李医生", dept: "影像科" },
    ]);
  });

  it("支持中文逗号分隔", () => {
    expect(parseExperts("王医生，外科")).toEqual([{ name: "王医生", dept: "外科" }]);
  });

  it("忽略空行与首尾空白", () => {
    expect(parseExperts("  \n 赵医生 \n\n")).toEqual([{ name: "赵医生" }]);
  });

  it("只有姓名时不带 dept/org", () => {
    expect(parseExperts("钱医生")).toEqual([{ name: "钱医生" }]);
  });

  it("空文本返回空数组", () => {
    expect(parseExperts("")).toEqual([]);
    expect(parseExperts("   ")).toEqual([]);
  });
});
