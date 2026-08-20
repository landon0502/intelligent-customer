"use client"

import { useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { Save, Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@intelligent-customer/ui/components/card"
import { Label } from "@intelligent-customer/ui/components/label"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@intelligent-customer/ui/components/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"

import {
  getConfigs,
  updateConfigs,
  toLlmConfig,
  fromLlmConfig,
  toEmbeddingConfig,
  fromEmbeddingConfig,
  toVectorStoreConfig,
  fromVectorStoreConfig,
  toRerankerConfig,
  fromRerankerConfig,
  toRagLlmConfig,
  fromRagLlmConfig,
  type LlmConfig,
  type EmbeddingConfig,
  type VectorStoreConfig,
  type RerankerConfig,
  type RagLlmConfig,
} from "@/services/config"

export default function ConfigPage() {
  const t = useTranslations("config")

  const [llm, setLlm] = useState<LlmConfig>({
    provider: "deepseek",
    model: "deepseek-v4-pro",
    api_key: "",
    base_url: "",
    temperature: "0.7",
    max_tokens: "512",
    timeout: "15",
    max_retries: "1",
  })
  const [embedding, setEmbedding] = useState<EmbeddingConfig>({
    provider: "local",
    model: "BAAI/bge-base-zh-v1.5",
    dimensions: "768",
  })
  const [vectorStore, setVectorStore] = useState<VectorStoreConfig>({
    provider: "chroma",
    host: "localhost",
    port: "8000",
    collection: "knowledge_base",
  })
  const [reranker, setReranker] = useState<RerankerConfig>({
    enabled: "false",
    model: "Qwen/Qwen3-Reranker-0.6B",
    device: "cpu",
    candidates: "20",
    recall_threshold: "0.1",
  })
  const [ragLlm, setRagLlm] = useState<RagLlmConfig>({
    model: "",
    api_key: "",
    base_url: "",
    temperature: "0.3",
    max_tokens: "512",
    timeout: "15",
    max_retries: "1",
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const items = await getConfigs()
        if (!cancelled) {
          setLlm(toLlmConfig(items))
          setEmbedding(toEmbeddingConfig(items))
          setVectorStore(toVectorStoreConfig(items))
          setReranker(toRerankerConfig(items))
          setRagLlm(toRagLlmConfig(items))
        }
      } catch {
        if (!cancelled) toast.error("加载配置失败")
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  // 保存配置
  const handleSave = async (category: string) => {
    setSaving(category)
    try {
      let configs
      if (category === "llm") configs = fromLlmConfig(llm)
      else if (category === "ragllm") configs = fromRagLlmConfig(ragLlm)
      else if (category === "embedding")
        configs = fromEmbeddingConfig(embedding)
      else if (category === "vectorstore")
        configs = fromVectorStoreConfig(vectorStore)
      else configs = fromRerankerConfig(reranker)

      await updateConfigs(configs)
      toast.success(t("save") + " ✓")
    } catch {
      toast.error(t("save") + " 失败")
    } finally {
      setSaving(null)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("title")}</h1>
      </div>

      <Tabs defaultValue="llm">
        <TabsList>
          <TabsTrigger value="llm">{t("tabLlm")}</TabsTrigger>
          <TabsTrigger value="ragllm">{t("tabRagLlm")}</TabsTrigger>
          <TabsTrigger value="embedding">{t("tabEmbedding")}</TabsTrigger>
          <TabsTrigger value="vectorstore">{t("tabVectorStore")}</TabsTrigger>
          <TabsTrigger value="reranker">{t("tabReranker")}</TabsTrigger>
        </TabsList>

        {/* LLM 配置 */}
        <TabsContent value="llm" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("llmTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t("llmProvider")}</Label>
                  <Input
                    value={llm.provider}
                    onChange={(e) => setLlm({ ...llm, provider: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmModel")}</Label>
                  <Input
                    value={llm.model}
                    onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmApiKey")}</Label>
                  <Input
                    type="password"
                    value={llm.api_key}
                    placeholder={llm.api_key ? "••••••••" : ""}
                    onChange={(e) =>
                      setLlm({ ...llm, api_key: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmBaseUrl")}</Label>
                  <Input
                    value={llm.base_url}
                    placeholder="请输入base_url"
                    onChange={(e) =>
                      setLlm({ ...llm, base_url: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmTemperature")}</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={llm.temperature}
                    onChange={(e) =>
                      setLlm({ ...llm, temperature: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmMaxTokens")}</Label>
                  <Input
                    type="number"
                    value={llm.max_tokens}
                    onChange={(e) =>
                      setLlm({ ...llm, max_tokens: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmTimeout")}</Label>
                  <Input
                    type="number"
                    value={llm.timeout}
                    onChange={(e) =>
                      setLlm({ ...llm, timeout: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("llmMaxRetries")}</Label>
                  <Input
                    type="number"
                    value={llm.max_retries}
                    onChange={(e) =>
                      setLlm({ ...llm, max_retries: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => handleSave("llm")}
                  disabled={saving === "llm"}
                >
                  {saving === "llm" ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {t("save")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* RAG LLM 配置 */}
        <TabsContent value="ragllm" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("ragLlmTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {t("ragLlmFallbackHint")}
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t("ragLlmModel")}</Label>
                  <Input
                    value={ragLlm.model}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, model: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmApiKey")}</Label>
                  <Input
                    type="password"
                    value={ragLlm.api_key}
                    placeholder={ragLlm.api_key ? "••••••••" : ""}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, api_key: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmBaseUrl")}</Label>
                  <Input
                    value={ragLlm.base_url}
                    placeholder="请输入base_url"
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, base_url: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmTemperature")}</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={ragLlm.temperature}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, temperature: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmMaxTokens")}</Label>
                  <Input
                    type="number"
                    value={ragLlm.max_tokens}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, max_tokens: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmTimeout")}</Label>
                  <Input
                    type="number"
                    value={ragLlm.timeout}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, timeout: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("ragLlmMaxRetries")}</Label>
                  <Input
                    type="number"
                    value={ragLlm.max_retries}
                    onChange={(e) =>
                      setRagLlm({ ...ragLlm, max_retries: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => handleSave("ragllm")}
                  disabled={saving === "ragllm"}
                >
                  {saving === "ragllm" ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {t("save")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Embedding 配置 */}
        <TabsContent value="embedding" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("embeddingTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t("embeddingProvider")}</Label>
                  <Input
                    value={embedding.provider}
                    onChange={(e) => setEmbedding({ ...embedding, provider: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("embeddingModel")}</Label>
                  <Input
                    value={embedding.model}
                    onChange={(e) =>
                      setEmbedding({ ...embedding, model: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("embeddingDimensions")}</Label>
                  <Input
                    type="number"
                    value={embedding.dimensions}
                    onChange={(e) =>
                      setEmbedding({ ...embedding, dimensions: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => handleSave("embedding")}
                  disabled={saving === "embedding"}
                >
                  {saving === "embedding" ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {t("save")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 向量数据库配置 */}
        <TabsContent value="vectorstore" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("vectorStoreTitle")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t("vsProvider")}</Label>
                  <Select
                    value={vectorStore.provider}
                    onValueChange={(v) =>
                      v && setVectorStore({ ...vectorStore, provider: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="chroma">Chroma</SelectItem>
                      <SelectItem value="milvus">Milvus</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>{t("vsHost")}</Label>
                  <Input
                    value={vectorStore.host}
                    onChange={(e) =>
                      setVectorStore({ ...vectorStore, host: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("vsPort")}</Label>
                  <Input
                    value={vectorStore.port}
                    onChange={(e) =>
                      setVectorStore({ ...vectorStore, port: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("vsCollection")}</Label>
                  <Input
                    value={vectorStore.collection}
                    onChange={(e) =>
                      setVectorStore({
                        ...vectorStore,
                        collection: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => handleSave("vectorstore")}
                  disabled={saving === "vectorstore"}
                >
                  {saving === "vectorstore" ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {t("save")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reranker 重排序配置 */}
        <TabsContent value="reranker" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("rerankerTitle")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t("rerankEnabled")}</Label>
                  <Select
                    value={reranker.enabled}
                    onValueChange={(v) =>
                      v && setReranker({ ...reranker, enabled: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="false">
                        {t("rerankDisabled")}
                      </SelectItem>
                      <SelectItem value="true">{t("rerankEnabledOn")}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>{t("rerankDevice")}</Label>
                  <Select
                    value={reranker.device}
                    onValueChange={(v) =>
                      v && setReranker({ ...reranker, device: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cpu">CPU</SelectItem>
                      <SelectItem value="mps">MPS</SelectItem>
                      <SelectItem value="cuda">CUDA</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>{t("rerankModel")}</Label>
                  <Input
                    value={reranker.model}
                    onChange={(e) =>
                      setReranker({ ...reranker, model: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("rerankCandidates")}</Label>
                  <Input
                    type="number"
                    min="1"
                    value={reranker.candidates}
                    onChange={(e) =>
                      setReranker({ ...reranker, candidates: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("rerankRecallThreshold")}</Label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={reranker.recall_threshold}
                    onChange={(e) =>
                      setReranker({
                        ...reranker,
                        recall_threshold: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => handleSave("reranker")}
                  disabled={saving === "reranker"}
                >
                  {saving === "reranker" ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {t("save")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
