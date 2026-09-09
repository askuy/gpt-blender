# 部署 Go 网页服务

服务使用 Go 标准库，把 `web/` 中的 HTML、CSS、JavaScript、GLB、镜头数据和 M4A 对白内置在一个可执行文件中。部署不需要 Python、Node.js、Blender 或额外资源目录；MP4、`reference/`、`output/` 和源码均不对外提供。

## 构建

在开发机使用 Go 1.26 或更新版本构建。目标为 Linux x86_64 时：

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o dist/niulai-linux-amd64 .
```

目标为 Linux ARM64 时：

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -ldflags='-s -w' -o dist/niulai-linux-arm64 .
```

在服务器上用 `uname -m` 确认架构：`x86_64` 对应 `amd64`，`aarch64` 对应 `arm64`。上传对应的文件，安装为 `/opt/niulai/niulai`，赋予可执行权限。更换网页或模型后需要重新构建并发布这个文件。

## 启动

使用已有反向代理提供 HTTPS 时，服务监听本机：

```sh
/opt/niulai/niulai --addr 127.0.0.1:8766
```

将现有站点的上游指向 `http://127.0.0.1:8766`，并保留 `Range` 和缓存校验请求头。建议在反向代理启用 JavaScript、JSON、CSS 和 GLB 的 gzip 压缩。服务通过 ETag 校验缓存，未变化的资源返回 304；支持音频分段请求。

如果暂时直接通过 IP 和端口访问：

```sh
/opt/niulai/niulai --addr :8766
```

网页地址是 `http://服务器IP:8766/`，需要相应端口已放行。旧的 `/web/` 地址会跳转到首页。

## systemd 常驻运行

仓库中的 `niulai.service` 使用独立动态用户运行，并监听 `127.0.0.1:8766`，适合接入已有反向代理。将二进制安装到上文路径后，在目标服务器执行：

```sh
sudo install -m 644 niulai.service /etc/systemd/system/niulai.service
sudo systemctl daemon-reload
sudo systemctl enable --now niulai
sudo systemctl status niulai --no-pager
curl --fail http://127.0.0.1:8766/healthz
```

发布新版本时保留上一份二进制以便回滚，替换文件后执行 `sudo systemctl restart niulai`，再检查健康状态和网页。发布到 opcops 管理的环境时，使用该环境的部署规范和控制面流程。

## 验证

开发机运行：

```sh
npm ci
npx playwright install chromium
npm test
```

其中 Go 测试验证公开资源范围、MP4 返回 404、模型缓存及音频 Range 请求；浏览器测试验证真实模型、音轨、字幕、时间轴、镜头和手机布局。

验证已发布的站点时，在开发机执行以下命令，将地址换为实际地址：

```sh
PREVIEW_URL=https://你的域名/ node src/verify.mjs
```

浏览器测试访问 `PREVIEW_URL`，不在本地另启服务；服务器不需要测试依赖。
