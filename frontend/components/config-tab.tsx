"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import axios from "axios"

interface ConfigData {
  [key: string]: any
}

export function ConfigTab() {
  const [config, setConfig] = useState<ConfigData>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await axios.get("http://localhost:8000/config")
      setConfig(response.data.config)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load configuration",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await axios.post("http://localhost:8000/config", { config })
      toast({
        title: "Success",
        description: "Configuration saved successfully"
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save configuration",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }))
  }

  if (loading) {
    return <div className="flex items-center justify-center p-8">Loading configuration...</div>
  }

  return (
    <div className="space-y-6">
      {/* Basic Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>基本配置 (Basic Configuration)</CardTitle>
          <CardDescription>设置爬虫的基本参数 (Set basic crawler parameters)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="platform">平台 (Platform)</Label>
              <Select value={config.PLATFORM || ""} onValueChange={(value) => handleInputChange("PLATFORM", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择平台" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="xhs">小红书 (Xiaohongshu)</SelectItem>
                  <SelectItem value="dy">抖音 (Douyin)</SelectItem>
                  <SelectItem value="ks">快手 (Kuaishou)</SelectItem>
                  <SelectItem value="bili">B站 (Bilibili)</SelectItem>
                  <SelectItem value="wb">微博 (Weibo)</SelectItem>
                  <SelectItem value="tieba">贴吧 (Tieba)</SelectItem>
                  <SelectItem value="zhihu">知乎 (Zhihu)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="login-type">登录类型 (Login Type)</Label>
              <Select value={config.LOGIN_TYPE || ""} onValueChange={(value) => handleInputChange("LOGIN_TYPE", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择登录方式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="qrcode">二维码登录 (QR Code)</SelectItem>
                  <SelectItem value="phone">手机号登录 (Phone)</SelectItem>
                  <SelectItem value="cookie">Cookie登录 (Cookie)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="crawler-type">爬虫类型 (Crawler Type)</Label>
              <Select value={config.CRAWLER_TYPE || ""} onValueChange={(value) => handleInputChange("CRAWLER_TYPE", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择爬虫类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="search">关键词搜索 (Search)</SelectItem>
                  <SelectItem value="detail">帖子详情 (Detail)</SelectItem>
                  <SelectItem value="creator">创作者主页 (Creator)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="save-data-option">数据保存方式 (Save Data Option)</Label>
              <Select value={config.SAVE_DATA_OPTION || ""} onValueChange={(value) => handleInputChange("SAVE_DATA_OPTION", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择保存方式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="csv">CSV 文件</SelectItem>
                  <SelectItem value="db">数据库 (Database)</SelectItem>
                  <SelectItem value="json">JSON 文件</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="keywords">关键词 (Keywords)</Label>
            <Input
              id="keywords"
              value={config.KEYWORDS || ""}
              onChange={(e) => handleInputChange("KEYWORDS", e.target.value)}
              placeholder="以英文逗号分隔 (Separated by commas)"
            />
          </div>
        </CardContent>
      </Card>

      {/* Crawler Settings */}
      <Card>
        <CardHeader>
          <CardTitle>爬虫设置 (Crawler Settings)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start-page">起始页数 (Start Page)</Label>
              <Input
                id="start-page"
                type="number"
                value={config.START_PAGE || ""}
                onChange={(e) => handleInputChange("START_PAGE", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-notes">最大爬取数量 (Max Notes Count)</Label>
              <Input
                id="max-notes"
                type="number"
                value={config.CRAWLER_MAX_NOTES_COUNT || ""}
                onChange={(e) => handleInputChange("CRAWLER_MAX_NOTES_COUNT", parseInt(e.target.value) || 200)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-comments">最大评论数量 (Max Comments Count)</Label>
              <Input
                id="max-comments"
                type="number"
                value={config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES || ""}
                onChange={(e) => handleInputChange("CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", parseInt(e.target.value) || 10)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="concurrency">并发数量 (Concurrency)</Label>
              <Input
                id="concurrency"
                type="number"
                value={config.MAX_CONCURRENCY_NUM || ""}
                onChange={(e) => handleInputChange("MAX_CONCURRENCY_NUM", parseInt(e.target.value) || 1)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="enable-comments"
                checked={config.ENABLE_GET_COMMENTS || false}
                onCheckedChange={(checked) => handleInputChange("ENABLE_GET_COMMENTS", checked)}
              />
              <Label htmlFor="enable-comments">启用评论爬取 (Enable Comments)</Label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="enable-sub-comments"
                checked={config.ENABLE_GET_SUB_COMMENTS || false}
                onCheckedChange={(checked) => handleInputChange("ENABLE_GET_SUB_COMMENTS", checked)}
              />
              <Label htmlFor="enable-sub-comments">启用二级评论 (Enable Sub Comments)</Label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="enable-images"
                checked={config.ENABLE_GET_IMAGES || false}
                onCheckedChange={(checked) => handleInputChange("ENABLE_GET_IMAGES", checked)}
              />
              <Label htmlFor="enable-images">启用图片下载 (Enable Images)</Label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="headless"
                checked={config.HEADLESS || false}
                onCheckedChange={(checked) => handleInputChange("HEADLESS", checked)}
              />
              <Label htmlFor="headless">无头模式 (Headless Mode)</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Proxy Settings */}
      <Card>
        <CardHeader>
          <CardTitle>代理设置 (Proxy Settings)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Switch
              id="enable-proxy"
              checked={config.ENABLE_IP_PROXY || false}
              onCheckedChange={(checked) => handleInputChange("ENABLE_IP_PROXY", checked)}
            />
            <Label htmlFor="enable-proxy">启用IP代理 (Enable IP Proxy)</Label>
          </div>

          {config.ENABLE_IP_PROXY && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="proxy-pool-count">代理池数量 (Proxy Pool Count)</Label>
                <Input
                  id="proxy-pool-count"
                  type="number"
                  value={config.IP_PROXY_POOL_COUNT || ""}
                  onChange={(e) => handleInputChange("IP_PROXY_POOL_COUNT", parseInt(e.target.value) || 2)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="proxy-provider">代理提供商 (Proxy Provider)</Label>
                <Input
                  id="proxy-provider"
                  value={config.IP_PROXY_PROVIDER_NAME || ""}
                  onChange={(e) => handleInputChange("IP_PROXY_PROVIDER_NAME", e.target.value)}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card>
        <CardHeader>
          <CardTitle>高级设置 (Advanced Settings)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="user-agent">User Agent</Label>
            <Textarea
              id="user-agent"
              value={config.UA || ""}
              onChange={(e) => handleInputChange("UA", e.target.value)}
              placeholder="自定义User Agent"
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="cookies">Cookies</Label>
            <Textarea
              id="cookies"
              value={config.COOKIES || ""}
              onChange={(e) => handleInputChange("COOKIES", e.target.value)}
              placeholder="登录用的Cookies"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="save-login-state"
                checked={config.SAVE_LOGIN_STATE || false}
                onCheckedChange={(checked) => handleInputChange("SAVE_LOGIN_STATE", checked)}
              />
              <Label htmlFor="save-login-state">保存登录状态 (Save Login State)</Label>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="enable-cdp"
                checked={config.ENABLE_CDP_MODE || false}
                onCheckedChange={(checked) => handleInputChange("ENABLE_CDP_MODE", checked)}
              />
              <Label htmlFor="enable-cdp">启用CDP模式 (Enable CDP Mode)</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving} size="lg">
          {saving ? "保存中..." : "保存配置 (Save Configuration)"}
        </Button>
      </div>
    </div>
  )
} 