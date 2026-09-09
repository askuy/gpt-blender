# 发布到 GitHub Pages

网站是完整的静态页面，发布目录为 `web/`。模型、音轨和 Three.js 都在这个目录中，动画由访问者的浏览器运行。线上不需要 Go、Python、Node.js 或数据库。

## 发布结构

- 开发仓库：`askuy/niulai`，保持私有。
- 网页发布仓库：`askuy/niulai-site`，公开且只保存 `web/` 的内容。
- 访问地址：**https://askuy.github.io/niulai-site/**。
- Saber 手办：**https://askuy.github.io/niulai-site/saber/**。

当前账号套餐不支持从私有仓库启用 Pages，因此使用独立的公开网页仓库免费托管。发布仓库在 **Settings → Pages** 中选择 **Deploy from a branch → main → /(root)**。推送网页资源后，GitHub 自动构建并发布。

## 更新网站

先运行 `npm test` 和 `npm run test:saber`，确认两个页面正常，然后执行：

```sh
npm run publish:pages -- --dry-run
npm run publish:pages
```

发布脚本在临时目录中克隆公开网页仓库，用当前 `web/` 替换发布文件，提交并推送 `main`。需要已有的 SSH 推送权限。脚本不会把开发仓库的历史、离线脚本、MP4 或 Blender 工程复制到公开仓库。`--dry-run` 只检查待发布差异，不推送。

页面使用相对路径，兼容 `/niulai-site/` 子目录；`.nojekyll` 用于跳过 Jekyll。更新后在发布仓库的 Actions 中检查 Pages 状态，再运行下文的线上验证。

## 本地预览

开发机安装 Node.js 22+ 后运行：

```sh
npm ci
npm run dev
```

默认打开 **http://127.0.0.1:8080/**；端口占用时以终端输出的地址为准。用 `npm run dev -- -p 8767` 可指定端口。本地预览仅提供 `web/` 中的文件。

浏览器的模块与资源请求需要通过 HTTP 访问，请使用预览地址打开页面。

## 验证

```sh
npx playwright install chromium
npm test
npm run test:saber
```

检查程序使用临时静态服务器，验证模型、音轨、字幕、时间轴、镜头和手机布局，并确认 MP4 与仓库源码未公开。

验证线上站点：

```sh
PREVIEW_URL=https://askuy.github.io/niulai-site/ npm test
PREVIEW_URL=https://askuy.github.io/niulai-site/ npm run test:saber
```

已有浏览器可通过 `CHROME_BIN=/path/to/chrome` 指定。报告写入 `output/verification.json`，截图写入 `renders/`。
