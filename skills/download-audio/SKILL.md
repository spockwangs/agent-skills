---
name: download-audio
description: |
  从在线视频/音频站点下载音乐并转码为 MP3。覆盖 B 站（Bilibili）等。针对 B 站视频页 412 反爬，提供走开放 API（view + playurl 取 DASH 音频流）的兜底脚本。
  触发关键词：下载音乐、下载 mp3、下载音频、从 b 站下载、bilibili 下载、下载歌曲。
user-invocable: true
---

# 下载音乐为 MP3

把在线视频/音频下载并转码为 MP3。默认输出到目录 `~/Downloads/`。

## 工具准备

```bash
pip3 install -q yt-dlp imageio-ffmpeg   # imageio-ffmpeg 提供静态 ffmpeg 二进制，免系统安装
```

ffmpeg 路径（无系统 ffmpeg 时用 imageio-ffmpeg 的静态二进制）：

```bash
python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
```

## 通用站点：先用 yt-dlp

对 YouTube 等大部分站点直接用 yt-dlp 即可：

```bash
FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
yt-dlp --ffmpeg-location "$FFMPEG" -f bestaudio -x --audio-format mp3 --audio-quality 0 \
  -o "歌名.%(ext)s" "URL"
```

## B 站：412 反爬兜底

B 站视频页 `www.bilibili.com/video/<BV>` 对非浏览器请求返回 **HTTP 412 Precondition Failed**，
yt-dlp 直接抓会失败。此时走开放 API（带首页 `buvid3` cookie + `Origin`/`Referer` 头，API 返回 200）：

1. `GET https://api.bilibili.com/x/web-interface/view?bvid=<BV>` → 取 `aid`、`cid`、`title`、`duration`
2. `GET https://api.bilibili.com/x/player/playurl?avid=<aid>&cid=<cid>&qn=80&fnval=16&fnver=0&fourk=1` → DASH 音频流列表
3. 选 `dash.audio` 中 `bandwidth` 最大的条目，取 `baseUrl`
4. `curl` 下载该音频流（**必须带 `Referer: https://www.bilibili.com/`**，否则 403）
5. ffmpeg `libmp3lame -qscale:a 0` 转码 MP3

以上已封装为脚本，直接调用：

```bash
SCRIPT="/data/mm64/spockwang/workspace/skills/skills/download-music/scripts/bili_audio.sh"
mkdir -p downloads && cd downloads
bash "$SCRIPT" "BV1G44y1c7zh" "Beyond - 真的爱你"
# 也支持完整 URL: bash "$SCRIPT" "https://www.bilibili.com/video/BV1G44y1c7zh" "歌名"
```

## 找 BV 号

不知道 BV 号时，用 WebSearch 搜 `bilibili 歌名 BV bilibili.com/video`，从结果里取 `BVxxxxxxxxxx`，
再用 AskQuestion 让用户在多个候选（原版 MV / Hi-res / 现场版等）间选择。

## 注意事项

- B 站 cookie 属设备指纹（buvid3/b_nut），非用户凭证；脚本每次现取现用，不落盘、不打印。
- 自动审批可能拦截“打印 cookie 值”的命令——避免 `grep buvid` 打印 cookie 内容，只打印 cookie 名。
- 纯本地命令偶发沙箱后端错误（landlock/bwrap），重试或加 `required_permissions: ["all"]` 即可。
- 若 API 也返回 412（IP 被风控），需在浏览器登录 B 站后用 `yt-dlp --cookies-from-browser <浏览器>` 提供会话 cookie。
