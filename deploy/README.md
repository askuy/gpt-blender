# 发布到 GitHub Pages

网站是完整的静态页面，发布目录为 `web/`。模型、音轨和 Three.js 都在这个目录中，动画由访问者的浏览器运行。线上不需要 Go、Python、Node.js 或数据库。

## 自动发布

1. 仓库管理员在 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。这项设置只需做一次。
2. 将代码推送到 `main`。修改 `web/` 或发布工作流时会自动部署；也可以在 **Actions → Deploy viewer to GitHub Pages → Run workflow** 手动部署。
3. 工作流只上传 `web/`，不需要构建步骤，也不安装开发依赖。MP4、Blender 文件和仓库源码不会发布到网站。
4. 部署成功后，站点地址为 **https://askuy.github.io/niulai/**。

页面使用相对路径，兼容 GitHub Pages 的 `/niulai/` 子目录。`.nojekyll` 标记用于跳过 Jekyll 处理。

公开仓库可使用免费 Pages；私有仓库需要支持私有仓库 Pages 的账号套餐。仓库可见性由所有者决定。

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
```

检查程序使用临时静态服务器，验证模型、音轨、字幕、时间轴、镜头和手机布局，并确认 MP4 与仓库源码未公开。

验证线上站点：

```sh
PREVIEW_URL=https://askuy.github.io/niulai/ npm test
```

已有浏览器可通过 `CHROME_BIN=/path/to/chrome` 指定。报告写入 `output/verification.json`，截图写入 `renders/`。
