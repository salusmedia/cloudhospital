// 全仓共享的 ESLint 扁平配置。关键：用 no-restricted-imports 强制"场景间禁止互相 import"。
// 各包：import base from "@hospital/config/eslint"; export default [...base, {/* 局部覆盖 */}];
export default [
  {
    rules: {
      // 依赖边界：禁止跨场景直接 import（场景之间必须走共享层或网关 HTTP）。
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/apps/scenario-*", "**/services/scenario-*", "@hospital/scenario-*"],
              message:
                "禁止跨场景直接 import。需要别的场景的数据/能力请走平台服务或网关 HTTP；共享类型放 @hospital/shared-types。",
            },
          ],
        },
      ],
    },
  },
];
