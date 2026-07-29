import { describe, expect, it } from "vitest";
import { filterMenuByRole, menuConfig } from "@/config/menu";

describe("filterMenuByRole", () => {
  it("admin 角色看到 chat 项 + management 分组（含 4 个子项）", () => {
    const result = filterMenuByRole(menuConfig, "admin");
    // 2 top-level entries: chat item + management group
    expect(result).toHaveLength(2);
    // chat (no roles) — visible to all
    expect(result.find((e) => e.key === "chat")).toBeDefined();
    // management group — preserved with its children
    const management = result.find((e) => e.key === "management");
    expect(management).toBeDefined();
    expect(management?.type).toBe("group");
    if (management?.type === "group") {
      expect(management.children).toHaveLength(4);
      expect(management.children?.map((c) => c.key).sort()).toEqual(
        ["config", "knowledge", "tools", "users"]
      );
    }
  });

  it("user 角色只看到 chat 菜单项（空分组被移除）", () => {
    const result = filterMenuByRole(menuConfig, "user");
    // Only chat remains; management group removed because all its children are admin-only
    expect(result).toHaveLength(1);
    expect(result.find((e) => e.key === "chat")).toBeDefined();
    expect(result.find((e) => e.key === "management")).toBeUndefined();
  });

  it("undefined role 返回空数组", () => {
    const result = filterMenuByRole(menuConfig, undefined);
    expect(result).toEqual([]);
  });

  it("分组下所有 item 被过滤时，分组被移除", () => {
    const entries = [
      { type: "group" as const, key: "admin-group", labelKey: "admin.group", children: [
        { key: "secret", labelKey: "secret", href: "/secret", icon: {} as any, roles: ["admin" as const] },
      ] },
      { key: "public", labelKey: "public", href: "/public", icon: {} as any },
    ];
    const result = filterMenuByRole(entries, "user");
    // Group removed (no visible children); only public item remains
    expect(result).toHaveLength(1);
    expect(result[0].key).toBe("public");
    expect(result.find((e) => e.key === "admin-group")).toBeUndefined();
  });

  it("分组下部分 item 被过滤时，仅保留可见子项", () => {
    const entries = [
      {
        type: "group" as const,
        key: "mixed-group",
        labelKey: "mixed.group",
        children: [
          { key: "admin-only", labelKey: "admin", href: "/admin", icon: {} as any, roles: ["admin" as const] },
          { key: "all-users", labelKey: "all", href: "/all", icon: {} as any },
        ],
      },
    ];
    const result = filterMenuByRole(entries, "user");
    expect(result).toHaveLength(1);
    const group = result[0];
    expect(group.type).toBe("group");
    if (group.type === "group") {
      expect(group.children).toHaveLength(1);
      expect(group.children?.[0].key).toBe("all-users");
    }
  });
});
