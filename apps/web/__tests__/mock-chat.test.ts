import { describe, it, expect } from "vitest";
import { mockGetAIResponse } from "@/config/mock-chat";

describe("mockGetAIResponse", () => {
  it("问候语关键词返回问候响应", () => {
    const result = mockGetAIResponse("你好");
    expect(result.content).toBeTruthy();
    expect(result.toolCalls).toBeUndefined();
  });

  it("英文 hi 也匹配问候", () => {
    const result = mockGetAIResponse("hi");
    expect(result.content).toBeTruthy();
    expect(result.toolCalls).toBeUndefined();
  });

  it("退货关键词返回退货政策 + toolCall", () => {
    const result = mockGetAIResponse("我想退货");
    expect(result.content).toContain("退货");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("search_knowledge_base");
  });

  it("订单关键词返回订单查询 + toolCall", () => {
    const result = mockGetAIResponse("查一下我的订单");
    expect(result.content).toContain("订单");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("query_order");
  });

  it("商品关键词返回商品推荐 + toolCall", () => {
    const result = mockGetAIResponse("推荐手机");
    expect(result.content).toContain("商品");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("search_products");
  });

  it("无匹配关键词返回默认回复", () => {
    const result = mockGetAIResponse("随便聊聊");
    expect(result.content).toContain("咨询");
    expect(result.toolCalls).toBeUndefined();
  });
});
