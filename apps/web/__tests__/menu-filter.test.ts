import { describe, expect, it } from "vitest";
import { filterMenuByRole, menuConfig } from "@/config/menu";

describe("filterMenuByRole", () => {
  it("admin 角色看到全部菜单项（5 item + 1 group = 6 entries）", () => {
    const result = filterMenuByRole(menuConfig, "admin");
    expect(result).toHaveLength(6);
    // chat (no roles) — visible to all
    expect(result.find((e) => e.key === "chat")).toBeDefined();
    // management group — always preserved
    expect(result.find((e) => e.key === "management")).toBeDefined();
    // admin-only items
    expect(result.find((e) => e.key === "knowledge")).toBeDefined();
    expect(result.find((e) => e.key === "users")).toBeDefined();
    expect(result.find((e) => e.key === "config")).toBeDefined();
    expect(result.find((e) => e.key === "tools")).toBeDefined();
  });

  it("user 角色只看到 chat 菜单项（1 item + 1 group = 2 entries）", () => {
    const result = filterMenuByRole(menuConfig, "user");
    expect(result).toHaveLength(2);
    // chat has no roles — visible to all
    expect(result.find((e) => e.key === "chat")).toBeDefined();
    // management group — always preserved even when no items visible under it
    expect(result.find((e) => e.key === "management")).toBeDefined();
    // admin-only items should be filtered out
    expect(result.find((e) => e.key === "knowledge")).toBeUndefined();
    expect(result.find((e) => e.key === "users")).toBeUndefined();
    expect(result.find((e) => e.key === "config")).toBeUndefined();
    expect(result.find((e) => e.key === "tools")).toBeUndefined();
  });

  it("undefined role 返回空数组", () => {
    const result = filterMenuByRole(menuConfig, undefined);
    expect(result).toEqual([]);
  });

  it("分组下所有 item 被过滤时，分组标题仍保留在结果中", () => {
    // Use a custom config where the group has no visible items for "user"
    const entries = [
      { type: "group" as const, key: "admin-group", labelKey: "admin.group" },
      { key: "secret", labelKey: "secret", href: "/secret", icon: {} as any, roles: ["admin" as const] },
    ];
    const result = filterMenuByRole(entries, "user");
    // Group is preserved even though its only item is filtered out
    expect(result).toHaveLength(1);
    expect(result[0].key).toBe("admin-group");
    expect(result[0].type).toBe("group");
  });
});
