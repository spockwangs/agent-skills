#!/usr/bin/env bash
# 从 B 站下载指定视频的音频并转码为 MP3。
# 用法: bili_audio.sh <BV号或完整URL> [输出文件名(不含扩展名)]
# 依赖: curl, python3, ffmpeg(或 imageio-ffmpeg)
#
# 设计说明: B 站视频页对非浏览器请求返回 HTTP 412 反爬，
# 但开放 API (/x/web-interface/view, /x/player/playurl) 带 buvid3 cookie
# 及 Origin/Referer 头可正常返回。本脚本走 API 取 DASH 音频流后下载转码。
set -euo pipefail

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
ORIGIN="https://www.bilibili.com"
REFERER="https://www.bilibili.com/"

INPUT="${1:?用法: bili_audio.sh <BV号或URL> [输出名]}"
BV=$(echo "$INPUT" | grep -oE 'BV[0-9A-Za-z]{10}' | head -1)
[ -z "$BV" ] && { echo "无法从输入解析 BV 号: $INPUT" >&2; exit 1; }
OUT="${2:-bili_audio}"

if command -v ffmpeg >/dev/null 2>&1; then
  FFMPEG=$(command -v ffmpeg)
elif python3 -c "import imageio_ffmpeg" 2>/dev/null; then
  FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
else
  echo "未找到 ffmpeg，请安装或 pip install imageio-ffmpeg" >&2; exit 1
fi

DEST_DIR="$PWD"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# 1. 取 buvid3 cookie
curl -s -A "$UA" -c jar.txt "$ORIGIN/" -o /dev/null
# 2. 视频元数据
curl -s -A "$UA" -b jar.txt -H "Origin: $ORIGIN" -H "Referer: $REFERER" \
  "https://api.bilibili.com/x/web-interface/view?bvid=$BV" -o view.json
META=$(python3 - <<'PY'
import json
d=json.load(open('view.json'))
assert d.get('code')==0, f"view API error: {d.get('message')}"
data=d['data']
print(data['aid'], data['cid'])
PY
)
AID=${META%% *}; CID=${META##* }
# 3. 播放地址 (DASH)
curl -s -A "$UA" -b jar.txt -H "Origin: $ORIGIN" -H "Referer: $REFERER" \
  "https://api.bilibili.com/x/player/playurl?avid=$AID&cid=$CID&qn=80&fnval=16&fnver=0&fourk=1" -o playurl.json
AUDIO_URL=$(python3 - <<'PY'
import json
d=json.load(open('playurl.json'))
assert d.get('code')==0, f"playurl API error: {d.get('message')}"
aud=d['data']['dash'].get('audio',[])
assert aud, "no audio stream"
aud.sort(key=lambda a:a.get('bandwidth',0), reverse=True)
print(aud[0].get('baseUrl') or aud[0].get('base_url'))
PY
)
# 4. 下载音频流 (必须带 Referer, 否则 403)
curl -s -A "$UA" -b jar.txt -H "Origin: $ORIGIN" -H "Referer: $REFERER" \
  "$AUDIO_URL" -o audio.m4s -w "audio HTTP %{http_code}, %{size_download} bytes\n"
# 5. 转码 MP3 (V0 最高质量)
"$FFMPEG" -y -loglevel error -i audio.m4s -codec:a libmp3lame -qscale:a 0 "$OUT.mp3"

FINAL="$DEST_DIR/$OUT.mp3"
mv "$OUT.mp3" "$FINAL"
echo "OK: $FINAL"
"$FFMPEG" -i "$FINAL" 2>&1 | grep -iE "Duration|Stream #0:0" | head -2
