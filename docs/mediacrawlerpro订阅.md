# 订阅MediaCrawlerPro版本源码访问权限

## 获取Pro版本的访问权限
> MediaCrawler开源超过一年了，相信该仓库帮过不少朋友低门槛的学习和了解爬虫。维护真的耗费了大量精力和人力 <br>
> 
> 所以Pro版本不会开源，可以订阅Pro版本让我更加有动力去更新。<br>
> 
> 如果感兴趣可以加我微信，订阅Pro版本访问权限哦，有门槛💰。<br>
> 
> 仅针对想学习Pro版本源码实现的用户，如果是公司或者商业化盈利性质的就不要加我了，谢谢🙏
> 
> 代码设计拓展性强，可以自己扩展更多的爬虫平台，更多的数据存储方式，相信对你架构这种爬虫代码有所帮助。
> 
> 
> **MediaCrawlerPro项目主页地址**
> [MediaCrawlerPro Github主页地址](https://github.com/MediaCrawlerPro)



扫描下方我的个人微信，备注：pro版本（如果图片展示不出来，可以直接添加我的微信号：relakkes）

![relakkes_weichat.JPG](static/images/relakkes_weichat.jpg)


##  Pro版本诞生的背景
[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)这个项目开源至今获得了大量的关注，同时也暴露出来了一系列问题，比如：
- 能否支持多账号？
- 能否在linux部署？
- 能否去掉playwright的依赖？
- 有没有更简单的部署方法？
- 有没有针对新手上门槛更低的方法？

诸如上面的此类问题，想要在原有项目上去动刀，无疑是增加了复杂度，可能导致后续的维护更加困难。
出于可持续维护、简便易用、部署简单等目的，对MediaCrawler进行彻底重构。

## 项目介绍
### [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)的Pro版本python实现
**小红书爬虫**，**抖音爬虫**， **快手爬虫**， **B站爬虫**， **微博爬虫**，**百度贴吧**，**知乎爬虫**...。

支持多种平台的爬虫，支持多种数据的爬取，支持多种数据的存储，最重要的**完美支持多账号+IP代理池，让你的爬虫更加稳定**。
相较于MediaCrawler，Pro版本最大的变化：
- 去掉了playwright的依赖，不再将Playwright集成到爬虫主干中，依赖过重。
- 增加了Docker，Docker-compose的方式部署，让部署更加简单。
- 多账号+IP代理池的支持，让爬虫更加稳定。
- 新增签名服务，解耦签名逻辑，让爬虫更加灵活。
