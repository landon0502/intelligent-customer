import { describe, it, expect, vi, beforeEach } from "vitest"

/**
 * 守「前端表单字段名 ↔ 后端接口参数名」这条最容易静默错配的缝：
 * 后端 `files: list[UploadFile] = File(...)`，字段名必须正好是 `files`，
 * 且每个文件各 append 一次（重复字段），而不是打包成数组塞一个字段。
 */
const { post } = vi.hoisted(() => ({ post: vi.fn() }))

vi.mock("@/lib/fetch", () => ({
  fetchClient: { post },
}))

const { uploadDocumentApi } = await import("@/services/knowledge")

/** 取唯一一次 post 调用的 (url, formData)，顺带断言确实只发了一次请求。 */
function firstPostCall(): [string, FormData] {
  expect(post).toHaveBeenCalledTimes(1)
  const call = post.mock.calls[0]
  if (!call) throw new Error("fetchClient.post 未被调用")
  return call as [string, FormData]
}

describe("uploadDocumentApi", () => {
  beforeEach(() => {
    post.mockReset()
    post.mockResolvedValue({ code: 0, message: "success", data: null })
  })

  it("把每个文件以重复的 files 字段提交给 /knowledge/upload", async () => {
    const a = new File(["hello"], "a.txt", { type: "text/plain" })
    const b = new File(["world"], "b.txt", { type: "text/plain" })

    await uploadDocumentApi([a, b])

    const [url, formData] = firstPostCall()
    expect(url).toBe("/knowledge/upload")
    expect(formData).toBeInstanceOf(FormData)

    const sent = formData.getAll("files")
    expect(sent).toHaveLength(2)
    expect((sent[0] as File).name).toBe("a.txt")
    expect((sent[1] as File).name).toBe("b.txt")
  })

  it("单个文件也走同一契约，字段名不变", async () => {
    await uploadDocumentApi([new File(["x"], "only.pdf")])

    const [, formData] = firstPostCall()
    expect(formData.getAll("files")).toHaveLength(1)
    expect(formData.getAll("file")).toHaveLength(0)
  })
})
