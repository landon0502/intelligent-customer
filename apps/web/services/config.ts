import { fetchClient } from "@/lib/fetch"

export interface ConfigItem {
  key: string
  value: string
  category: string
  description?: string
}

export interface LlmConfig {
  provider: string
  model: string
  api_key: string
  base_url: string
  temperature: string
  max_tokens: string
  timeout: string
  max_retries: string
}

export interface EmbeddingConfig {
  provider: string
  model: string
  dimensions: string
}

export interface VectorStoreConfig {
  provider: string
  host: string
  port: string
  collection: string
}

export interface RerankerConfig {
  enabled: string
  model: string
  device: string
  candidates: string
  recall_threshold: string
}

/** 获取所有配置 */
export async function getConfigs(category?: string): Promise<ConfigItem[]> {
  const params = category ? `?category=${category}` : ""
  const response = await fetchClient.get<ConfigItem[]>(`/config${params}`)
  return response.data
}

/** 批量更新配置 */
export async function updateConfigs(
  configs: ConfigItem[]
): Promise<{ updated: number }> {
  const response = await fetchClient.put<{ updated: number }>("/config", {
    configs,
  })
  return response.data
}

/** 配置项列表 → LlmConfig 对象 */
export function toLlmConfig(items: ConfigItem[]): LlmConfig {
  const map = Object.fromEntries(items.map((i) => [i.key, i.value]))
  return {
    provider: map["llm.provider"] ?? "deepseek",
    model: map["llm.model"] ?? "deepseek-v4-pro",
    api_key: map["llm.api_key"] ?? "",
    base_url: map["llm.base_url"] ?? "",
    temperature: map["llm.temperature"] ?? "0.7",
    max_tokens: map["llm.max_tokens"] ?? "512",
    timeout: map["llm.timeout"] ?? "15",
    max_retries: map["llm.max_retries"] ?? "1",
  }
}

/** LlmConfig 对象 → 配置项列表 */
export function fromLlmConfig(cfg: LlmConfig): ConfigItem[] {
  return [
    { key: "llm.provider", value: cfg.provider, category: "llm" },
    { key: "llm.model", value: cfg.model, category: "llm" },
    { key: "llm.api_key", value: cfg.api_key, category: "llm" },
    { key: "llm.base_url", value: cfg.base_url, category: "llm" },
    { key: "llm.temperature", value: cfg.temperature, category: "llm" },
    { key: "llm.max_tokens", value: cfg.max_tokens, category: "llm" },
    { key: "llm.timeout", value: cfg.timeout, category: "llm" },
    { key: "llm.max_retries", value: cfg.max_retries, category: "llm" },
  ]
}

/** 配置项列表 → EmbeddingConfig 对象 */
export function toEmbeddingConfig(items: ConfigItem[]): EmbeddingConfig {
  const map = Object.fromEntries(items.map((i) => [i.key, i.value]))
  return {
    provider: map["embedding.provider"] ?? "local",
    model: map["embedding.model"] ?? "BAAI/bge-base-zh-v1.5",
    dimensions: map["embedding.dimensions"] ?? "768",
  }
}

/** EmbeddingConfig 对象 → 配置项列表 */
export function fromEmbeddingConfig(cfg: EmbeddingConfig): ConfigItem[] {
  return [
    { key: "embedding.provider", value: cfg.provider, category: "embedding" },
    { key: "embedding.model", value: cfg.model, category: "embedding" },
    {
      key: "embedding.dimensions",
      value: cfg.dimensions,
      category: "embedding",
    },
  ]
}

/** 配置项列表 → VectorStoreConfig 对象 */
export function toVectorStoreConfig(items: ConfigItem[]): VectorStoreConfig {
  const map = Object.fromEntries(items.map((i) => [i.key, i.value]))
  return {
    provider: map["vectorstore.provider"] ?? "chroma",
    host: map["vectorstore.host"] ?? "localhost",
    port: map["vectorstore.port"] ?? "8000",
    collection: map["vectorstore.collection"] ?? "knowledge_base",
  }
}

/** VectorStoreConfig 对象 → 配置项列表 */
export function fromVectorStoreConfig(cfg: VectorStoreConfig): ConfigItem[] {
  return [
    {
      key: "vectorstore.provider",
      value: cfg.provider,
      category: "vectorstore",
    },
    { key: "vectorstore.host", value: cfg.host, category: "vectorstore" },
    { key: "vectorstore.port", value: cfg.port, category: "vectorstore" },
    {
      key: "vectorstore.collection",
      value: cfg.collection,
      category: "vectorstore",
    },
  ]
}

/** 配置项列表 → RerankerConfig 对象 */
export function toRerankerConfig(items: ConfigItem[]): RerankerConfig {
  const map = Object.fromEntries(items.map((i) => [i.key, i.value]))
  return {
    enabled: map["rerank.enabled"] ?? "false",
    model: map["rerank.model"] ?? "Qwen/Qwen3-Reranker-0.6B",
    device: map["rerank.device"] ?? "cpu",
    candidates: map["rerank.candidates"] ?? "20",
    recall_threshold: map["rerank.recall_threshold"] ?? "0.1",
  }
}

/** RerankerConfig 对象 → 配置项列表 */
export function fromRerankerConfig(cfg: RerankerConfig): ConfigItem[] {
  return [
    { key: "rerank.enabled", value: cfg.enabled, category: "rerank" },
    { key: "rerank.model", value: cfg.model, category: "rerank" },
    { key: "rerank.device", value: cfg.device, category: "rerank" },
    { key: "rerank.candidates", value: cfg.candidates, category: "rerank" },
    {
      key: "rerank.recall_threshold",
      value: cfg.recall_threshold,
      category: "rerank",
    },
  ]
}
