"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ConfigTab } from "@/components/config-tab"
import { CrawlerTab } from "@/components/crawler-tab"
import { Settings, Play } from "lucide-react"

export default function Home() {
  return (
    <main className="container mx-auto py-8 px-4">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold mb-4">
          MediaCrawler 管理界面
        </h1>
        <p className="text-xl text-muted-foreground">
          多平台社交媒体数据采集工具管理界面 (Multi-platform Social Media Data Collection Tool)
        </p>
      </div>

      <Tabs defaultValue="config" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            配置管理 (Configuration)
          </TabsTrigger>
          <TabsTrigger value="crawler" className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            爬虫执行 (Crawler)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="config">
          <ConfigTab />
        </TabsContent>

        <TabsContent value="crawler">
          <CrawlerTab />
        </TabsContent>
      </Tabs>

      <footer className="mt-16 text-center text-sm text-muted-foreground">
        <p>
          MediaCrawler - 开源多平台社媒数据采集工具 | 
          <a 
            href="https://github.com/NanmiCoder/MediaCrawler" 
            target="_blank" 
            rel="noopener noreferrer"
            className="ml-1 underline hover:text-foreground"
          >
            GitHub
          </a>
        </p>
        <p className="mt-2">
          ⚠️ 请遵守平台使用条款，仅用于学习研究目的 (Please comply with platform terms of use, for learning and research purposes only)
        </p>
      </footer>
    </main>
  )
} 