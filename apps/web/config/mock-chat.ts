export interface ToolCall {
  name: string;
  display: string;
  status: "calling" | "done";
  summary: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  toolCalls?: ToolCall[];
}

export interface Session {
  id: string;
  title: string;
  time: string;
  messages: Message[];
}

export function mockGetAIResponse(text: string): {
  content: string;
  toolCalls?: ToolCall[];
} {
  const lower = text.toLowerCase();

  if (/你好|hi|hello/.test(lower)) {
    const greetings = [
      "你好！我是智能客服助手，有什么可以帮您的吗？",
      "您好！欢迎咨询，请问有什么问题？",
      "Hi！很高兴为您服务，请告诉我您的需求。",
    ];
    return {
      content: greetings[Math.floor(Math.random() * greetings.length)],
    };
  }

  if (/退货|换货|售后/.test(lower)) {
    return {
      content:
        "根据我们的退货政策，商品在购买后 **7 天内** 可以无理由退货。\n\n退货流程：\n1. 在订单详情页点击「申请退货」\n2. 填写退货原因\n3. 等待审核通过\n4. 寄回商品\n5. 收到退款\n\n> 退货运费由买家承担，商品需保持原包装完好。",
      toolCalls: [
        {
          name: "search_knowledge_base",
          display: "搜索知识库：退货政策",
          status: "done",
          summary: "找到退货政策文档 3 篇",
        },
      ],
    };
  }

  if (/订单|物流|快递/.test(lower)) {
    return {
      content:
        "正在为您查询订单信息...\n\n| 订单号 | 状态 | 预计到达 |\n|--------|------|----------|\n| ORD-20240115 | 运输中 | 1月18日 |\n| ORD-20240110 | 已签收 | - |\n\n如需查看详细物流信息，请提供具体订单号。",
      toolCalls: [
        {
          name: "query_order",
          display: "查询订单状态",
          status: "done",
          summary: "查询到 2 条订单记录",
        },
      ],
    };
  }

  if (/商品|产品|手机/.test(lower)) {
    return {
      content:
        "为您推荐以下商品：\n\n**智能手机 Pro Max**\n- 价格：¥5,999\n- 存储：256GB\n- 屏幕：6.7 英寸 OLED\n\n**智能手表 S3**\n- 价格：¥1,299\n- 续航：7 天\n- 防水：IP68\n\n如需了解更多详情，请告诉我具体商品名称。",
      toolCalls: [
        {
          name: "search_products",
          display: "搜索商品信息",
          status: "done",
          summary: "找到 2 个相关商品",
        },
      ],
    };
  }

  return {
    content:
      "感谢您的咨询。我目前可以帮您处理以下问题：\n\n- 退货/换货/售后问题\n- 订单/物流查询\n- 商品信息咨询\n\n请描述您的具体需求，我会尽力为您解答。",
  };
}

export const mockSessions: Session[] = [
  {
    id: "s1",
    title: "退货政策咨询",
    time: "2024-01-15 14:30",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "你好，我想了解一下退货政策",
        time: "14:30",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "根据我们的退货政策，商品在购买后 **7 天内** 可以无理由退货。\n\n退货流程：\n1. 在订单详情页点击「申请退货」\n2. 填写退货原因\n3. 等待审核通过\n4. 寄回商品\n5. 收到退款\n\n> 退货运费由买家承担，商品需保持原包装完好。",
        time: "14:30",
        toolCalls: [
          {
            name: "search_knowledge_base",
            display: "搜索知识库：退货政策",
            status: "done",
            summary: "找到退货政策文档 3 篇",
          },
        ],
      },
    ],
  },
  {
    id: "s2",
    title: "订单查询",
    time: "2024-01-15 10:15",
    messages: [
      {
        id: "m3",
        role: "user",
        content: "帮我查一下最近的订单",
        time: "10:15",
      },
      {
        id: "m4",
        role: "assistant",
        content:
          "正在为您查询订单信息...\n\n| 订单号 | 状态 | 预计到达 |\n|--------|------|----------|\n| ORD-20240115 | 运输中 | 1月18日 |\n| ORD-20240110 | 已签收 | - |\n\n如需查看详细物流信息，请提供具体订单号。",
        time: "10:15",
        toolCalls: [
          {
            name: "query_order",
            display: "查询订单状态",
            status: "done",
            summary: "查询到 2 条订单记录",
          },
        ],
      },
    ],
  },
  {
    id: "s3",
    title: "商品咨询",
    time: "2024-01-14 16:00",
    messages: [
      {
        id: "m5",
        role: "user",
        content: "有什么手机推荐吗？",
        time: "16:00",
      },
      {
        id: "m6",
        role: "assistant",
        content:
          "为您推荐以下商品：\n\n**智能手机 Pro Max**\n- 价格：¥5,999\n- 存储：256GB\n- 屏幕：6.7 英寸 OLED\n\n**智能手表 S3**\n- 价格：¥1,299\n- 续航：7 天\n- 防水：IP68\n\n如需了解更多详情，请告诉我具体商品名称。",
        time: "16:00",
        toolCalls: [
          {
            name: "search_products",
            display: "搜索商品信息",
            status: "done",
            summary: "找到 2 个相关商品",
          },
        ],
      },
    ],
  },
];
