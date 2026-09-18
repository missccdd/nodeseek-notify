# NodeSeek Notify

NodeSeek 通知工具：把「私信、回复我、@我」推到 Telegram，并支持每日签到。

---

## 1. 这个项目能做什么

启动后，脚本会定时检查 NodeSeek：

* 有人给你发私信 → Telegram 通知
* 有人回复你的主题/评论 → Telegram 通知
* 有人 @你 → Telegram 通知
* 每天到点自动签到（成功只写日志，失败才通知）

---

## 2. 你需要提前准备的东西

准备这 4 样即可：

1. 一台 Linux 服务器（或你自己的电脑），能打开这两个网站：
   * `https://www.nodeseek.com`
   * `https://api.telegram.org`
2. 服务器已安装 Python 3.10 或更高版本
3. 一个 Telegram 账号
4. 一个已经登录的 NodeSeek 账号

---

## 3. 创建 Telegram 机器人

### 3.1 创建 Bot，拿到 Token

1. 打开 Telegram，搜索 [`@BotFather`](https://t.me/BotFather)
2. 发送：`/newbot`
3. 按提示起名字，例如：`我的 NodeSeek 通知`
4. 再起一个用户名，必须以 `bot` 结尾，例如：`my_ns_notify_bot`
5. BotFather 会发给你一串 Token，类似：

```text
1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> 这一串就是 `bot_token`。不要发给任何人，也不要提交到 GitHub。

### 3.2 拿到 Chat ID

1. 先给刚创建的机器人发一句任意文字，例如：`hello`
2. 然后用浏览器打开（把 `你的TOKEN` 换成上一步的 Token）：

```text
https://api.telegram.org/bot你的TOKEN/getUpdates
```

3. 在打开的页面里找 `"chat":{"id":` 后面的数字。常见两种：
   * 发给自己：正数，例如 `123456789`
   * 发到群/频道：负数，例如 `-1001234567890`

> **提示：**
> * 如果页面几乎是空的：再给机器人发一条消息，然后刷新这个链接。
> * 如果要推到群里：把机器人拉进群，在群里发一条消息，再打开上面的 `getUpdates` 链接复制群的 `chat.id`。

这个数字就是 `chat_id`。

---

## 4. 获取 NodeSeek Cookie

Cookie 相当于登录凭证。有了它，脚本才能替你查看私信和签到。

### 4.1 用浏览器插件导出（强烈推荐，最快）

安装其中一个插件：
* **Cookie-Editor**（Chrome / Edge / Firefox 都有）
* **EditThisCookie**

然后按下面做：
1. 用浏览器打开并登录 `https://www.nodeseek.com`
2. 确认已经登录成功（能看到自己的头像/用户名）
3. 点击插件图标
4. 点击 **Export**
5. 选择 **JSON** 格式导出
6. 把导出的内容保存成文件，文件名必须是：`cookies.json`

> 插件导出的 JSON 已经是程序能读的格式，一般不用再改结构。

### 4.2 建议删掉的字段

导出后，建议删掉名为 `__cf_ob` 的那一项（一般在 JSON 的最后一段）。
* **原因：** 它通常非常长，一般不需要，留着有时容易出问题。

**建议保留这些（有就留）：**
* `session`（最重要，登录身份）
* `pjwt`（用来识别“这是我自己”，从而不推自己发出的私信）
* `smac`
* `fog`
* `hmti_`
* `colorscheme`
* `cf_clearance`（如果有, 建议保留, 有助于过 Cloudflare）

### 4.3 cookies.json 应该长什么样

真正使用时，`value` 必须是你自己导出的值。下面只是格式示例，不要原样拿去用：

```json
[
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": false,
    "name": "fog",
    "path": "/",
    "sameSite": null,
    "secure": false,
    "session": false,
    "value": "YOUR_FOG_VALUE"
  },
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": false,
    "name": "colorscheme",
    "path": "/",
    "sameSite": null,
    "secure": false,
    "session": false,
    "value": "light"
  },
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": false,
    "name": "hmti_",
    "path": "/",
    "sameSite": null,
    "secure": false,
    "session": false,
    "value": "YOUR_HMTI_VALUE"
  },
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": false,
    "name": "pjwt",
    "path": "/",
    "sameSite": "lax",
    "secure": false,
    "session": false,
    "value": "YOUR_PJWT_VALUE"
  },
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": true,
    "name": "session",
    "path": "/",
    "sameSite": "lax",
    "secure": false,
    "session": false,
    "value": "YOUR_SESSION_VALUE"
  },
  {
    "domain": "www.nodeseek.com",
    "hostOnly": true,
    "httpOnly": false,
    "name": "smac",
    "path": "/",
    "sameSite": "lax",
    "secure": false,
    "session": false,
    "value": "YOUR_SMAC_VALUE"
  }
]
```

### 4.4 Cookie 安全提醒

* `cookies.json` 等于账号密码，谁拿到谁能登录你的号。
* 不要发到群里、不要提交到 GitHub。
* 如果已经不小心发过，立刻在 NodeSeek 退出登录，重新登录，再导出一份新的。

---

## 5. 安装项目

下面以服务器路径 `/root/nodeseek-notify` 为例。你要装到别的目录，把路径一起换掉。

### 5.1 下载项目

```bash
cd /root
git clone https://github.com/missccdd/nodeseek-notify.git
cd nodeseek-notify
```

### 5.2 创建 Python 虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

以后每次手动测试，都要先执行：

```bash
cd /root/nodeseek-notify
source venv/bin/activate
```

看到命令行前面出现 `(venv)` 就说明环境激活成功了。

### 5.3 放入 Cookie 文件

把刚才导出的 `cookies.json` 放到项目目录：

```text
/root/nodeseek-notify/cookies.json
```

可用下面命令确认文件在不在：

```bash
ls -l /root/nodeseek-notify/cookies.json
```

---

## 6. 填写配置文件

### 6.1 从模板文件复制一份配置

```bash
cp config.example.yaml config.yaml
```

以后只改 `config.yaml`。其中有密钥，不能公开。

### 6.2 最小必填项

用编辑器打开：

```bash
nano config.yaml
```

至少改这两处：

```yaml
telegram:
  bot_token: "1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  chat_id: "123456789"
```

* **说明：**
  * `bot_token`：第 3 步从 BotFather 拿到的 Token。
  * `chat_id`：第 3 步从 getUpdates 里拿到的数字（如果是群，一般是负数，把负号一起填上）。

> **保存方法：** 在 nano 编辑器中按 `Ctrl + O` 回车保存，再按 `Ctrl + X` 退出。

### 6.3 其他常用配置（可先不改）

```yaml
checkin:
  enabled: true         # 是否开启每日签到
  hour: 8               # 每天 8 点后才签到
  random: false         # true=随机鸡腿，false=固定签到

notify:
  private_message: true  # 推私信
  reply_to_me: true      # 推“回复我”
  at_me: true            # 推“@我”
  skip_outgoing_pm: true # 自己发出的私信不推
  force_bootstrap: false # true=本轮只记已读不推送
```

> **小白建议：** 第一次先全部保持默认，只填 Token 和 Chat ID。如果启动后发现「自己发给别人的私信还是会推」，再在配置里填：

```yaml
nodeseek:
  my_user_id: "12345"     # 改成你主页 URL 里的数字 ID
  my_username: "你的用户名"
```

个人空间地址一般是：`https://www.nodeseek.com/space/数字ID`，那个数字就是 `my_user_id`。

---

## 7. 先手动运行，确认没问题

```bash
cd /root/nodeseek-notify
source venv/bin/activate
python notify.py
```

正常时，终端大致会看到：

```text
============================================================
NodeSeek 通知/签到脚本启动
配置文件: /root/nodeseek-notify/config.yaml
Cookie 文件: /root/nodeseek-notify/cookies.json
============================================================
冷启动：已静默记录 xx 条，不推送
```

同时 Telegram 会收到一条：

```text
NodeSeek 通知/签到监控已启动
```

> **提示：** 第一次启动会把当前已有的私信/回复/@先记下来，但不会把历史消息全部推过来。这是为了防止刷屏。

**测试是否正常：**
1. 让朋友给你发一条 NodeSeek 私信（或让朋友回复你的帖子 / @你）。
2. 大约 1 分钟内，Telegram 应该收到通知。

停止前台运行：按 `Ctrl + C`。

---

## 8. 用 systemd 做成后台服务（推荐）

这样关掉 SSH 窗口后，脚本还会继续跑，挂了也会自动重启。

### 8.1 确认服务文件里的路径

打开项目自带的服务模板：

```bash
nano deploy/nodeseek-notify.service
```

确认这几行和你的实际路径一致：

```ini
WorkingDirectory=/root/nodeseek-notify
ExecStart=/root/nodeseek-notify/venv/bin/python /root/nodeseek-notify/notify.py
```

如果你不是装在 `/root/nodeseek-notify`，这里必须改。

### 8.2 安装并启动服务

```bash
sudo cp deploy/nodeseek-notify.service /etc/systemd/system/nodeseek-notify.service
sudo systemctl daemon-reload
sudo systemctl enable --now nodeseek-notify
```

查看是否在跑：

```bash
sudo systemctl status nodeseek-notify
```

看到 `active (running)` 就成功了。

**看实时日志：**

```bash
sudo journalctl -u nodeseek-notify -f
```

*(退出日志界面：按 `Ctrl + C`，这只是退出查看，不会停止服务)*

**常用命令：**

```bash
# 停止
sudo systemctl stop nodeseek-notify

# 启动
sudo systemctl start nodeseek-notify

# 重启（改完配置或 Cookie 后用这个）
sudo systemctl restart nodeseek-notify

# 开机自启
sudo systemctl enable nodeseek-notify
```

---

## 9. Telegram 会通知哪些情况

**会推送到机器人：**
* 脚本启动 / 手动停止
* Cookie 失效
* Cookie 从失效恢复
* 每日签到失败
* 脚本主循环异常、进程崩溃
* 新的私信 / 回复我 / @我

**默认不推：**
* 某个通知接口偶尔超时、返回空数据（脚本会在日志里记录，并在下一轮自动重试，避免网络抖一下就刷屏）。
* 你自己发给别人的私信（默认开启过滤）。

---

## 10. 常见问题

### 10.1 Telegram 收不到“监控已启动”
* **检查：**
  * `config.yaml` 里的 `bot_token`、`chat_id` 有没有填错。
  * 有没有先给机器人发过消息。
  * 如果是群，机器人有没有被拉进群，有没有发言权限。
  * 看终端有没有 Telegram 发送失败。

### 10.2 提示 Cookie 无效 / 过期
* **常见原因：**
  * `cookies.json` 不是登录后导出的。
  * 浏览器里已经退出登录。
  * 漏了 `session`。
  * 导出后过了很久才放到服务器。
* **处理：** 重新登录 NodeSeek，重新用插件导出，覆盖服务器上的 `cookies.json`，然后执行：

```bash
sudo systemctl restart nodeseek-notify
```

### 10.3 自己发给别人的私信还是会推到 Telegram
在 `config.yaml` 填写：

```yaml
nodeseek:
  my_user_id: "你的数字ID"
  my_username: "你的用户名"
```

保存后重启服务。

### 10.4 第一次启动推了一堆旧消息
把配置改成：

```yaml
notify:
  force_bootstrap: true
```

重启跑一轮，确认日志出现“冷启动/静默记录”后，再改回：

```yaml
notify:
  force_bootstrap: false
```

然后再次重启。

### 10.5 签到没有执行
* **检查：**
  * `checkin.enabled` 是不是 `true`。
  * 服务器当前时间是否已经过了 `checkin.hour`。
  * Cookie 是否有效。
  * `checkin_state.json` 里的 `last_date` 是不是已经是今天（是的话表示今天已经签过）。
* 查看服务器时间：`date`

### 10.6 服务启动失败
先看日志：

```bash
sudo journalctl -u nodeseek-notify -n 100 --no-pager
```

再确认：`venv` 是否已经 `pip install -r requirements.txt`、`config.yaml` 是否存在、`cookies.json` 是否存在、服务文件里的路径是否写对。

---

## 11. 配置项一览

完整说明见 `config.example.yaml`。常用项如下：

| 配置项 | 作用 | 小白建议 |
| :--- | :--- | :--- |
| `telegram.bot_token` | 机器人 Token | 必填 |
| `telegram.chat_id` | 接收通知的聊天 ID | 必填 |
| `nodeseek.cookie_file` | Cookie 文件路径 | 默认 `cookies.json` |
| `nodeseek.my_user_id` | 你的 NodeSeek 数字 ID | 过滤自己私信失败时再填 |
| `checkin.enabled` | 是否签到 | 默认开启 |
| `checkin.hour` | 几点后签到 | 默认 `8` |
| `checkin.random` | 是否随机鸡腿 | 默认关闭 |
| `notify.private_message` | 是否推私信 | 默认开启 |
| `notify.reply_to_me` | 是否推回复 | 默认开启 |
| `notify.at_me` | 是否推@我 | 默认开启 |
| `notify.skip_outgoing_pm` | 忽略自己发出的私信 | 默认开启 |
| `notify.force_bootstrap` | 本轮只记已读不推送 | 默认关闭 |
| `intervals.notify_check` | 检查通知间隔（秒） | 默认 `60` |

---

## 12. 安全建议

* 不要把 `config.yaml`、`cookies.json` 传到 GitHub。
* 仓库里只保留 `config.example.yaml`。
* Token 或 Cookie 泄漏后立刻作废并更换。
* 服务器权限能收紧就收紧，不要把项目目录公开成网站目录。
