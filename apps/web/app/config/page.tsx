"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Save } from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Card, CardContent, CardHeader, CardTitle } from "@intelligent-customer/ui/components/card"
import { Label } from "@intelligent-customer/ui/components/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@intelligent-customer/ui/components/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"

// 模拟配置数据
const mockLlmConfig = {
  provider: "zhipu",
  model: "glm-4.5-air",
  temperature: "0.7",
  maxTokens: "1000",
  timeout: "30",
  maxRetries: "2",
}

const mockEmbeddingConfig = {
  provider: "zhipu",
  model: "embedding-3",
  dimensions: "2048",
}

const mockVectorStoreConfig = {
  provider: "chroma",
  host: "127.0.0.1",
  port: "8000",
  collection: "intelligent_customer",
}

export default function ConfigPage() {
  const t = useTranslations("config")

  const [llm, setLlm] = useState(mockLlmConfig)
  const [embedding, setEmbedding] = useState(mockEmbeddingConfig)
  const [vectorStore, setVectorStore] = useState(mockVectorStoreConfig)

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">{t("title")}</h1>
        </div>

        <Tabs defaultValue="llm">
          <TabsList>
            <TabsTrigger value="llm">{t("tabLlm")}</TabsTrigger>
            <TabsTrigger value="embedding">{t("tabEmbedding")}</TabsTrigger>
            <TabsTrigger value="vectorstore">{t("tabVectorStore")}</TabsTrigger>
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
                    <Select value={llm.provider} onValueChange={(v) => v && setLlm({ ...llm, provider: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zhipu">{t("providerZhipu")}</SelectItem>
                        <SelectItem value="deepseek">{t("providerDeepseek")}</SelectItem>
                        <SelectItem value="openai">{t("providerOpenai")}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>{t("llmModel")}</Label>
                    <Input value={llm.model} onChange={(e) => setLlm({ ...llm, model: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("llmTemperature")}</Label>
                    <Input type="number" step="0.1" min="0" max="2" value={llm.temperature} onChange={(e) => setLlm({ ...llm, temperature: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("llmMaxTokens")}</Label>
                    <Input type="number" value={llm.maxTokens} onChange={(e) => setLlm({ ...llm, maxTokens: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("llmTimeout")}</Label>
                    <Input type="number" value={llm.timeout} onChange={(e) => setLlm({ ...llm, timeout: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("llmMaxRetries")}</Label>
                    <Input type="number" value={llm.maxRetries} onChange={(e) => setLlm({ ...llm, maxRetries: e.target.value })} />
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <Button><Save className="size-4 mr-2" />{t("save")}</Button>
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
                    <Select value={embedding.provider} onValueChange={(v) => v && setEmbedding({ ...embedding, provider: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zhipu">{t("providerZhipu")}</SelectItem>
                        <SelectItem value="openai">{t("providerOpenai")}</SelectItem>
                        <SelectItem value="local">{t("providerLocal")}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>{t("embeddingModel")}</Label>
                    <Input value={embedding.model} onChange={(e) => setEmbedding({ ...embedding, model: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("embeddingDimensions")}</Label>
                    <Input type="number" value={embedding.dimensions} onChange={(e) => setEmbedding({ ...embedding, dimensions: e.target.value })} />
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <Button><Save className="size-4 mr-2" />{t("save")}</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 向量数据库配置 */}
          <TabsContent value="vectorstore" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t("vectorStoreTitle")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>{t("vsProvider")}</Label>
                    <Select value={vectorStore.provider} onValueChange={(v) => v && setVectorStore({ ...vectorStore, provider: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="chroma">Chroma</SelectItem>
                        <SelectItem value="milvus">Milvus</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>{t("vsHost")}</Label>
                    <Input value={vectorStore.host} onChange={(e) => setVectorStore({ ...vectorStore, host: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("vsPort")}</Label>
                    <Input value={vectorStore.port} onChange={(e) => setVectorStore({ ...vectorStore, port: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("vsCollection")}</Label>
                    <Input value={vectorStore.collection} onChange={(e) => setVectorStore({ ...vectorStore, collection: e.target.value })} />
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <Button><Save className="size-4 mr-2" />{t("save")}</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}
