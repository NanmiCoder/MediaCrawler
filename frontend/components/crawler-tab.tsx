"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { Textarea } from "@/components/ui/textarea"
import { Play, Terminal } from "lucide-react"
import axios from "axios"

interface CommandOptions {
  platforms: Array<{ value: string; label: string }>
  login_types: Array<{ value: string; label: string }>
  crawler_types: Array<{ value: string; label: string }>
  save_data_options: Array<{ value: string; label: string }>
}

interface CrawlerCommand {
  platform: string
  login_type: string
  crawler_type: string
  keywords?: string
  start_page?: number
  get_comment?: boolean
  get_sub_comment?: boolean
  save_data_option?: string
  cookies?: string
}

export function CrawlerTab() {
  const [options, setOptions] = useState<CommandOptions>({
    platforms: [],
    login_types: [],
    crawler_types: [],
    save_data_options: []
  })
  const [command, setCommand] = useState<CrawlerCommand>({
    platform: "",
    login_type: "",
    crawler_type: ""
  })
  const [isRunning, setIsRunning] = useState(false)
  const [output, setOutput] = useState("")
  const [error, setError] = useState("")
  const { toast } = useToast()

  useEffect(() => {
    fetchCommandOptions()
  }, [])

  const fetchCommandOptions = async () => {
    try {
      const response = await axios.get("http://localhost:8000/command-options")
      setOptions(response.data)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load command options",
        variant: "destructive"
      })
    }
  }

  const generateCommandString = () => {
    let cmd = `uv run main.py --platform ${command.platform} --lt ${command.login_type} --type ${command.crawler_type}`
    
    if (command.keywords) {
      cmd += ` --keywords "${command.keywords}"`
    }
    if (command.start_page && command.start_page > 1) {
      cmd += ` --start ${command.start_page}`
    }
    if (command.get_comment !== undefined) {
      cmd += ` --get_comment ${command.get_comment ? 'true' : 'false'}`
    }
    if (command.get_sub_comment !== undefined) {
      cmd += ` --get_sub_comment ${command.get_sub_comment ? 'true' : 'false'}`
    }
    if (command.save_data_option) {
      cmd += ` --save_data_option ${command.save_data_option}`
    }
    if (command.cookies) {
      cmd += ` --cookies "${command.cookies}"`
    }
    
    return cmd
  }

  const handleRunCommand = async () => {
    if (!command.platform || !command.login_type || !command.crawler_type) {
      toast({
        title: "Error",
        description: "Please select platform, login type, and crawler type",
        variant: "destructive"
      })
      return
    }

    setIsRunning(true)
    setOutput("")
    setError("")
    
    try {
      const response = await axios.post("http://localhost:8000/run-crawler", command)
      
      if (response.data.success) {
        setOutput(response.data.output || "Command executed successfully")
        toast({
          title: "Success",
          description: "Crawler executed successfully"
        })
      } else {
        setError(response.data.error || "Command failed")
        toast({
          title: "Error",
          description: "Crawler execution failed",
          variant: "destructive"
        })
      }
    } catch (error) {
      setError("Failed to execute command")
      toast({
        title: "Error",
        description: "Failed to execute crawler",
        variant: "destructive"
      })
    } finally {
      setIsRunning(false)
    }
  }

  const isValidCommand = command.platform && command.login_type && command.crawler_type

  return (
    <div className="space-y-6">
      {/* Command Builder */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            命令构建器 (Command Builder)
          </CardTitle>
          <CardDescription>配置并执行爬虫命令 (Configure and execute crawler commands)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Required Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="platform">平台 (Platform) *</Label>
              <Select value={command.platform} onValueChange={(value) => setCommand(prev => ({ ...prev, platform: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="选择平台" />
                </SelectTrigger>
                <SelectContent>
                  {options.platforms.map((platform) => (
                    <SelectItem key={platform.value} value={platform.value}>
                      {platform.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="login-type">登录类型 (Login Type) *</Label>
              <Select value={command.login_type} onValueChange={(value) => setCommand(prev => ({ ...prev, login_type: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="选择登录方式" />
                </SelectTrigger>
                <SelectContent>
                  {options.login_types.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="crawler-type">爬虫类型 (Crawler Type) *</Label>
              <Select value={command.crawler_type} onValueChange={(value) => setCommand(prev => ({ ...prev, crawler_type: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="选择爬虫类型" />
                </SelectTrigger>
                <SelectContent>
                  {options.crawler_types.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Optional Parameters */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">可选参数 (Optional Parameters)</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="keywords">关键词 (Keywords)</Label>
                <Input
                  id="keywords"
                  value={command.keywords || ""}
                  onChange={(e) => setCommand(prev => ({ ...prev, keywords: e.target.value }))}
                  placeholder="搜索关键词"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="start-page">起始页数 (Start Page)</Label>
                <Input
                  id="start-page"
                  type="number"
                  min="1"
                  value={command.start_page || ""}
                  onChange={(e) => setCommand(prev => ({ ...prev, start_page: parseInt(e.target.value) || undefined }))}
                  placeholder="1"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="save-data-option">数据保存方式 (Save Data Option)</Label>
                <Select value={command.save_data_option || ""} onValueChange={(value) => setCommand(prev => ({ ...prev, save_data_option: value }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择保存方式" />
                  </SelectTrigger>
                  <SelectContent>
                    {options.save_data_options.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="get-comment"
                  checked={command.get_comment || false}
                  onCheckedChange={(checked) => setCommand(prev => ({ ...prev, get_comment: checked }))}
                />
                <Label htmlFor="get-comment">启用评论爬取 (Enable Comments)</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="get-sub-comment"
                  checked={command.get_sub_comment || false}
                  onCheckedChange={(checked) => setCommand(prev => ({ ...prev, get_sub_comment: checked }))}
                />
                <Label htmlFor="get-sub-comment">启用二级评论 (Enable Sub Comments)</Label>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cookies">Cookies (Cookie登录时使用)</Label>
              <Textarea
                id="cookies"
                value={command.cookies || ""}
                onChange={(e) => setCommand(prev => ({ ...prev, cookies: e.target.value }))}
                placeholder="仅在Cookie登录时填写"
                rows={2}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Command Preview */}
      <Card>
        <CardHeader>
          <CardTitle>命令预览 (Command Preview)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted p-4 rounded-md font-mono text-sm">
            <code>{isValidCommand ? generateCommandString() : "请选择必需的参数 (Please select required parameters)"}</code>
          </div>
        </CardContent>
      </Card>

      {/* Execute Button */}
      <div className="flex justify-center">
        <Button 
          onClick={handleRunCommand} 
          disabled={!isValidCommand || isRunning}
          size="lg"
          className="w-full md:w-auto"
        >
          <Play className="h-4 w-4 mr-2" />
          {isRunning ? "执行中... (Running...)" : "运行爬虫 (Run Crawler)"}
        </Button>
      </div>

      {/* Output Display */}
      {(output || error) && (
        <Card>
          <CardHeader>
            <CardTitle>执行结果 (Execution Result)</CardTitle>
          </CardHeader>
          <CardContent>
            {output && (
              <div className="mb-4">
                <Label>输出 (Output):</Label>
                <pre className="bg-muted p-4 rounded-md text-sm mt-2 whitespace-pre-wrap overflow-auto max-h-64">
                  {output}
                </pre>
              </div>
            )}
            
            {error && (
              <div>
                <Label className="text-destructive">错误 (Error):</Label>
                <pre className="bg-destructive/10 border border-destructive/20 p-4 rounded-md text-sm mt-2 whitespace-pre-wrap overflow-auto max-h-64">
                  {error}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Commands */}
      <Card>
        <CardHeader>
          <CardTitle>快速命令 (Quick Commands)</CardTitle>
          <CardDescription>常用命令模板 (Common command templates)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "xhs",
                login_type: "qrcode",
                crawler_type: "search",
                keywords: "编程副业",
                get_comment: true
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">小红书搜索</div>
              <div className="text-xs text-muted-foreground mt-1">XHS Search with Comments</div>
            </Button>

            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "dy",
                login_type: "qrcode",
                crawler_type: "search",
                keywords: "编程教程",
                get_comment: true
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">抖音搜索</div>
              <div className="text-xs text-muted-foreground mt-1">Douyin Search with Comments</div>
            </Button>

            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "bili",
                login_type: "qrcode",
                crawler_type: "search",
                keywords: "python教程",
                get_comment: true
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">B站搜索</div>
              <div className="text-xs text-muted-foreground mt-1">Bilibili Search with Comments</div>
            </Button>

            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "xhs",
                login_type: "qrcode",
                crawler_type: "detail"
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">小红书详情</div>
              <div className="text-xs text-muted-foreground mt-1">XHS Detail Crawling</div>
            </Button>

            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "wb",
                login_type: "qrcode",
                crawler_type: "search",
                keywords: "科技新闻",
                get_comment: true
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">微博搜索</div>
              <div className="text-xs text-muted-foreground mt-1">Weibo Search with Comments</div>
            </Button>

            <Button
              variant="outline"
              onClick={() => setCommand({
                platform: "zhihu",
                login_type: "qrcode",
                crawler_type: "search",
                keywords: "人工智能",
                get_comment: true
              })}
              className="h-auto p-4 flex-col items-start"
            >
              <div className="font-medium">知乎搜索</div>
              <div className="text-xs text-muted-foreground mt-1">Zhihu Search with Comments</div>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 