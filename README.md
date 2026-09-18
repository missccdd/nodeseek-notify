# NodeSeek Notify

独立脚本：监听 NodeSeek 私信、回复我、@我，并做每日签到。  

## 功能

- 私信 / 回复主题 / @我 推送到 Telegram
- 每日签到（成功仅日志，失败才通知）
- 首次启动静默记录存量，避免历史消息刷屏
- 配置与密钥分离，适合快速部署


## 准备

1. 一台能访问 `www.nodeseek.com` 和 `api.telegram.org` 的服务器
2. Python 3.10+
3. Telegram Bot Token 和 Chat ID
4. NodeSeek 登录 Cookie

## 获取 Cookie

1. 浏览器登录 [NodeSeek](https://www.nodeseek.com/)
2. 打开开发者工具 -> Application/存储 -> Cookies
3. 导出为 `cookies.json`

推荐格式：

```json
[
  {"name": "session", "value": "xxx"},
  {"name": "pjwt", "value": "xxx"},
  {"name": "cf_clearance", "value": "xxx"}
]
