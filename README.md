# tool100_automail

一个基于 Flask + MailSlurp 的临时邮箱管理工具，用于批量创建测试邮箱、同步邮箱列表、查看收件箱邮件和邮件详情。项目提供网页操作台和 JSON API，适合注册测试、邮件验证码接收、邮件内容排查等场景。

## 功能

- 批量创建 MailSlurp 邮箱，单次支持 1 到 50 个。
- 支持选择邮箱后缀：`zazamail.link`、`temprelay.net`、`slurpinbox.com`。
- 同步 MailSlurp 账号下已有邮箱到本地记录。
- 查看每个邮箱的邮件列表。
- 查看邮件主题、发件人、收件人、正文、HTML 预览和源码。
- 前端支持手动刷新和自动刷新。
- 使用本地 JSON 文件保存邮箱索引，不依赖数据库。
- 支持通过 Git tag 自动发布到 Vercel。

## 技术栈

- Python 3
- Flask
- MailSlurp Python SDK
- Bootstrap 5
- Vercel
- GitHub Actions

## 目录结构

```text
.
├── app.py                     # Flask 入口和 API 路由
├── config.py                  # 应用配置和环境变量读取
├── requirements.txt           # Python 依赖
├── env.example                # 环境变量示例
├── index.html                 # Vercel 静态入口
├── vercel.json                # Vercel 项目配置
├── providers/                 # 邮箱服务 provider
├── services/                  # 邮箱业务逻辑和 JSON 存储
├── static/                    # 前端 CSS/JS
├── templates/                 # Flask 模板
└── .github/workflows/main.yml # tag 触发的 Vercel 发布流程
```

## 必要配置

本项目必须配置 MailSlurp API Key，否则创建邮箱和读取邮件会失败。

本地开发可以复制 `env.example` 为 `.env`：

```bash
cp env.example .env
```

然后填写：

```env
MAIL_PROVIDER=mailslurp
MAILSLURP_API_KEY=你的_MailSlurp_API_Key
MAIL_POLL_INTERVAL_MS=10000
APP_HOST=0.0.0.0
APP_PORT=9211
```

配置说明：

| 变量名 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MAIL_PROVIDER` | 否 | `mailslurp` | 当前只实现了 MailSlurp provider。 |
| `MAILSLURP_API_KEY` | 是 | 空 | MailSlurp API Key。 |
| `MAIL_POLL_INTERVAL_MS` | 否 | `10000` | 前端自动刷新间隔，单位毫秒。 |
| `APP_HOST` | 否 | `0.0.0.0` | 本地 Flask 监听地址。 |
| `APP_PORT` | 否 | `9211` | 本地 Flask 监听端口。 |
| `DATA_DIR` | 否 | `data` | JSON 数据目录。本地默认 `data/`，Vercel 默认 `/tmp/tools100-mail-auto`。 |

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
python app.py
```

打开：

```text
http://localhost:9211
```

## Vercel 环境变量

部署到 Vercel 后，不要把 `.env` 上传到仓库，也不要把密钥写进代码。需要在 Vercel 项目里配置运行时环境变量：

1. 打开 Vercel Dashboard。
2. 进入当前项目。
3. 打开 `Settings` -> `Environment Variables`。
4. 添加：

```text
Name: MAILSLURP_API_KEY
Value: 你的 MailSlurp API Key
Environment: Production
```

保存后需要重新部署一次，新的 Production Deployment 才会读取到变量。

## GitHub Actions 自动发布

项目已配置 `.github/workflows/main.yml`，推送 `v*` 格式的 tag 会自动发布到 Vercel Production。

GitHub 仓库需要配置以下 Actions Secrets：

```text
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

配置位置：

```text
GitHub 仓库 -> Settings -> Secrets and variables -> Actions
```

发布示例：

```bash
git tag v1.0.3
git push origin v1.0.3
```

workflow 会执行：

1. 安装 `uv`，用于 Vercel Python 构建。
2. 安装 Vercel CLI。
3. 检查 Vercel secrets 是否配置。
4. 拉取 Vercel Production 环境。
5. 执行 `vercel build --prod`。
6. 执行 `vercel deploy --prebuilt --prod`。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/summary` | 获取邮箱数量、邮件数量、最近同步时间等汇总信息。 |
| `GET` | `/api/mailboxes` | 获取本地记录的邮箱列表。 |
| `GET` | `/api/mailboxes?refresh=1` | 刷新邮箱邮件后返回邮箱列表。 |
| `POST` | `/api/mailboxes` | 创建邮箱。请求体示例：`{"count": 1, "domain_option": "zazamail.link"}`。 |
| `POST` | `/api/mailboxes/sync` | 从 MailSlurp 同步账号下已有邮箱。 |
| `GET` | `/api/mailboxes/<mailbox_id>/emails` | 获取指定邮箱的邮件列表。 |
| `GET` | `/api/mailboxes/<mailbox_id>/emails?refresh=1` | 先刷新再获取指定邮箱的邮件列表。 |
| `GET` | `/api/emails/<email_id>` | 获取指定邮件详情。 |

## 数据存储说明

项目使用 JSON 文件保存邮箱索引和同步状态：

```text
data/mailboxes.json
```

本地运行时默认写入项目目录下的 `data/`。Vercel Serverless 环境中，持久化文件系统不可用，因此默认写入 `/tmp/tools100-mail-auto`。这意味着 Vercel 上的数据可能随函数实例重启而丢失；如果需要长期保存邮箱索引，后续应接入数据库或 KV 存储。

## 注意事项

- `.env`、`data/`、`logs/`、`.venv/` 不应提交到 Git。
- Vercel 上的 `MAILSLURP_API_KEY` 要配置在项目 Environment Variables，不是 GitHub Secrets。
- GitHub Secrets 里的 `VERCEL_TOKEN`、`VERCEL_ORG_ID`、`VERCEL_PROJECT_ID` 只用于 CI 发布。
- 当前只支持 MailSlurp，切换其它邮箱服务需要新增 provider 实现。
- 单次创建邮箱数量限制为 1 到 50，避免误操作或触发服务限制。
