# Kindle 信息屏

一台闲置的 Kindle Voyage（横屏）变成桌面信息屏：全屏时钟 / 日历+待办面板 / AI 新闻，底部按钮切换。整页零动画，0/3/6/9/12/15/18/21 点整自动重载。

## 链路

```
GitHub Actions（每 3 小时）──> data/live.json ──┐
                                              ├──> GitHub Pages ──> Kindle 浏览器
WorkBuddy 自动化（每天早 8 点）─> data/local.json ┘
```

- **live.json**：哈尔滨天气 + AIHOT 新闻，Actions 在 GitHub 服务器上抓，跟 Mac 无关
- **local.json**：本机日历最近 4 条日程 + 提醒事项「待办」未完成项，Mac 上抓完推送
- 时钟是页面 JS 本地走的，不依赖网络；整点整页重载一次拿新数据

## 在你 Mac 上启用（一次性）

```bash
# 1. 克隆（用 HTTPS；SSH 在部分网络环境不通）
git clone https://github.com/ztow/kindle-screen.git ~/kindle-screen
cd ~/kindle-screen

# 2. 让裸 git push 复用 gh 的登录态（WorkBuddy 自动化推送时要用）
git config credential.helper '!gh auth git-credential'

# 3. 手动试跑一次（会弹「允许控制日历/提醒事项」的隐私授权框，点允许）
/opt/homebrew/bin/python3 scripts/fetch_local.py
```

## 定时更新（已配好）

- **日历/待办**：WorkBuddy 自动化任务「Kindle 信息屏 · 每日更新日历待办」，每天早 8:00 跑一次 `scripts/fetch_local.py` 并推送。想改时间：WorkBuddy → 自动化 → 找到该任务改触发时间
- **天气/新闻**：GitHub Actions 每 3 小时（北京时间 0/3/6/9/12/15/18/21 点整）自己抓自己提交，跟 Mac 在不在线无关
- 注意：本机数据一天一更，当天新增的日程/待办要等第二天早上才上屏；天气/新闻始终是 3 小时内新鲜的

## Kindle 侧

1. 连 2.4GHz WiFi（Voyage 不支持 5G）
2. β 浏览器打开 `https://ztow.github.io/kindle-screen/`，加书签
3. 建议 USB 常插电；屏幕休眠唤醒后会自动回到页面

## 改配置

| 想改什么 | 改哪里 |
|---|---|
| 城市/天气源坐标 | `scripts/fetch_live.py` 顶部 `CITY / LAT / LON` |
| 新闻条数 | `scripts/fetch_live.py` 顶部 `MAX_NEWS` |
| 待办列表名 | `scripts/fetch_local.py` 顶部 `REMINDER_LIST` |
| 日程条数 | `scripts/fetch_local.py` 顶部 `MAX_EVENTS` |
| local.json 不要 base64 包装 | `scripts/fetch_local.py` 顶部 `OBFUSCATE = False` |

改完 `fetch_live.py` 推送即生效（Actions 下次整点跑）；改完 `fetch_local.py` 推送后，在 `~/kindle-screen` 里 `git pull` 一下（自动化每次拉最新代码跑）。

## 手动触发

- Actions 立刻跑一次：GitHub 仓库页 → Actions → update-live → Run workflow
- Mac 侧立刻跑一次：`cd ~/kindle-screen && python3 scripts/fetch_local.py`

## 隐私说明

仓库是公开的（GitHub 免费账号开 Pages 必须公开）。天气和新闻本来就是公开信息；`local.json` 默认做了 base64 包装，防的是顺手搜到，不防有心人——日程和待办终究会以可解码形式出现在公开 URL 上。介意的话：① 升级 GitHub Pro 把仓库转私有（Pages 照常）；② 或回到「Mac 常开本地服务」方案，告诉我即可。

## 排障

- **Kindle 打不开 github.io**：2014 年的浏览器 TLS 根证书可能太老。先拿手机/电脑确认网址本身通；Kindle 上不行就得换方案（Mac 本地服务 / 越狱）
- **WorkBuddy 自动化失败**：看自动化的运行记录报错。常见两种：① git 认证失败——确认 `~/kindle-screen` 里配了 `git config credential.helper '!gh auth git-credential'`；② osascript 隐私授权没给上——在 Terminal 里手动跑一次 `~/kindle-screen/scripts/fetch_local.py`，弹窗点允许
- **Actions 失败**：仓库 Actions 页看日志，多半是网络抖动，重跑即可
- **页面显示空**：`data/local.json` 还是初始占位符，等 Mac 侧首跑；`data/live.json` 等 Actions 首跑（约 1 分钟）
