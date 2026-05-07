# SellerSprite Lite

一个本地运行的亚马逊商品采集与分析助手。

这版项目的目标很直接：

- 在关键词库里直接发起采集
- 把采到的商品沉淀到本地商品库
- 在商品库里筛选、收藏、备注、排序
- 用 DeepSeek 对商品库、收藏夹、关键词库做分析
- 双击 `exe` 后自动启动本地服务并打开网页

## 当前版本在做什么

这是一个可分发、可本地运行的 `SellerSprite Lite`。

当前前端主流程是：

1. 新增关键词
2. 选择类目和采集数量
3. 在关键词行里点 `采集`
4. 在商品库里筛选和收藏
5. 在收藏夹里集中查看重点商品
6. 需要价格历史时跳转 `Keepa` / `CamelCamelCamel`
7. 需要总结建议时让 `DeepSeek` 分析当前数据

## 当前功能

### 1. 关键词库

- 新增关键词
- 设置站点、类目参数、优先级、备注
- 设置状态：`active / paused / archived`
- 每个关键词可直接触发采集
- 支持自定义本次采集数量

### 2. 商品库

- 按关键词抓取亚马逊搜索结果
- 保存标题、ASIN、站点、价格、评分、评论数、Prime、Sponsored、品牌、排名、机会分
- 支持搜索、筛选、分页、排序
- 支持收藏、备注、状态管理、删除
- 支持打开商品页
- 支持跳转 `Keepa` / `Camel` 查看外部价格历史

### 3. 收藏夹

- 自动展示你在商品库里点过 `收藏` 的商品
- 适合沉淀重点商品
- 支持直接打开商品页
- 支持直接跳转外部价格历史页面

### 4. AI 分析

- 接入 `DeepSeek`
- 可分析：
  - `商品库`
  - `收藏夹`
  - `关键词库`
- API Key 只保留在当前程序运行期间
- 关闭程序后，Key 不会保存到本地

### 5. 数据看板

- 商品总数
- 关键词总数
- 收藏数量
- 平均价格
- 平均评分
- 最近采集记录
- 关键词表现概览

## 项目结构

最重要的文件可以这样看：

- [launcher.py](C:/Users/15068/Desktop/亚马逊网站/launcher.py)
  负责 `exe` 启动、本地服务拉起、浏览器自动打开

- [app/main.py](C:/Users/15068/Desktop/亚马逊网站/app/main.py)
  FastAPI 主入口，所有前端接口都从这里进

- [app/config.py](C:/Users/15068/Desktop/亚马逊网站/app/config.py)
  全局配置，例如数据库路径、抓取超时、请求头、默认站点

- [app/runtime.py](C:/Users/15068/Desktop/亚马逊网站/app/runtime.py)
  处理源码模式和 `exe` 模式下的数据目录差异

- [app/database.py](C:/Users/15068/Desktop/亚马逊网站/app/database.py)
  初始化 SQLite 表结构和索引

- [app/schemas.py](C:/Users/15068/Desktop/亚马逊网站/app/schemas.py)
  请求参数和响应模型定义

- [app/services/amazon_scraper.py](C:/Users/15068/Desktop/亚马逊网站/app/services/amazon_scraper.py)
  真实抓取亚马逊搜索页的核心逻辑

- [app/services/product_repository.py](C:/Users/15068/Desktop/亚马逊网站/app/services/product_repository.py)
  商品库的增删改查、机会分计算、收藏逻辑

- [app/services/intel_repository.py](C:/Users/15068/Desktop/亚马逊网站/app/services/intel_repository.py)
  关键词库、采集记录、看板统计相关逻辑

- [app/services/deepseek_service.py](C:/Users/15068/Desktop/亚马逊网站/app/services/deepseek_service.py)
  DeepSeek 数据组装与 API 调用

- [app/services/ai_settings.py](C:/Users/15068/Desktop/亚马逊网站/app/services/ai_settings.py)
  当前运行时的 AI Key / 模型设置，现为内存级，不落盘

- [app/static/index.html](C:/Users/15068/Desktop/亚马逊网站/app/static/index.html)
  页面结构

- [app/static/app.js](C:/Users/15068/Desktop/亚马逊网站/app/static/app.js)
  前端交互逻辑、按钮事件、接口调用

- [app/static/styles.css](C:/Users/15068/Desktop/亚马逊网站/app/static/styles.css)
  页面样式

## 运行方式

### exe 模式

双击打包后的：

```text
SellerSpriteLite.exe
```

程序会自动：

- 启动本地 FastAPI 服务
- 自动寻找空闲端口
- 自动打开浏览器

## 数据存储

数据库使用 `SQLite`。

开发模式下：

- 默认数据库在项目目录附近

`exe` 模式下：

- 数据保存在 `exe` 同目录的 `data` 文件夹

核心数据库文件通常是：

```text
data/amazon_hardware.db
```

## 采集说明

当前采集方式是：

- 通过 `requests` 直接请求亚马逊搜索结果页
- 解析 HTML 中的商品卡片
- 抽取商品信息后入库

你现在可以在关键词区自己选择采集数量，范围是：

- `10 - 200`

后端会按目标数量自动估算最多翻几页，而不是固定只抓 1 页。

## 为什么有时会报 503

这不是数据库问题，也不是页面问题，通常是亚马逊对抓取请求的限制。

当前采集器在这里真正发请求：

- [app/services/amazon_scraper.py](C:/Users/15068/Desktop/亚马逊网站/app/services/amazon_scraper.py)

当亚马逊返回：

- `503 Service Unavailable`
- 验证页
- 机器人检测页

程序就会采集失败。

常见原因：

- 亚马逊把当前请求识别成爬虫流量
- 同一 IP 请求过频
- 某些站点或类目风控更严格
- 当前关键词触发了更严格的反爬策略

也就是说：

- 程序成功发出了请求
- 但亚马逊没有返回可正常解析的商品结果页

## 使用建议

- 先用少量采集，比如 `10` 或 `20`
- 同一关键词不要连续高频采集
- 先导入演示数据熟悉页面，再抓真实数据

## 打包说明

项目当前已经适配 `PyInstaller` 打包。

关键文件：

- [AmazonHardwareLauncher.spec](C:/Users/15068/Desktop/亚马逊网站/AmazonHardwareLauncher.spec)

产物是：

- 一个可直接双击运行的 `SellerSpriteLite.exe`

