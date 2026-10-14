# -*- coding: utf-8 -*-
"""
打包：把 texts/ 里的文本做成两种形态，塞进同一个 index.html

  ① 离线快照（内嵌）—— 双击 index.html 就能直接看、直接复制，不需要任何服务
  ② 实时读取   —— 部署到 GitHub Pages 后，页面优先 fetch texts/ 文件夹，
                   所以往文件夹里丢新 txt，刷新（或点「🔄 重新读取」）就出现

用法：
    python build.py

GitHub 上不需要本地跑 Python：.github/workflows/update-manifest.yml 会在你 push
texts/ 里的新文件后自动更新清单并重新打包 index.html。
"""

import base64, json, pathlib, re, sys

BASE  = pathlib.Path(__file__).resolve().parent
TPL   = BASE / "template.html"
OUT   = BASE / "index.html"
TEXTS = BASE / "texts"
COVER = BASE / "cover.jpg"
EXTS  = {".txt", ".md", ".json", ".js", ".css", ".html", ".log", ".csv"}
SKIP  = {"index.json"}
REPO  = "yukiskr/copy"      # 用于「清单落后时自动发现新文件」，与部署目标保持一致


def natural_key(name: str):
    """数字感知排序键：数字段按数值比、文字段按编码比，
    与页面里的 naturalCompare 语义一致（注意：不能把 int 和 str 混在一个元组里比）"""
    key = []
    for part in re.findall(r"\d+|\D+", name.lower()):
        key.append((0, int(part), "") if part.isdigit() else (1, 0, part))
    return key


def read_text(p: pathlib.Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return p.read_text(encoding=enc).replace("\r\n", "\n").rstrip("\n")
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").rstrip("\n")


def check_manifest(path: pathlib.Path):
    """清单是页面的“花名册”，坏了页面就一片空白。
    这里主动校验（而不是等页面出问题），坏了直接报错 —— Action 会显示红色，一眼能看到。"""
    if not path.is_file():
        return
    raw = path.read_bytes()
    if not raw.strip():
        raise SystemExit(f"[!] {path.name} 是空文件（{len(raw)} 字节）—— 请删掉它再跑一次，"
                         f"或从 git 历史里恢复一个正常版本")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"[!] {path.name} 不是合法 JSON（{len(raw)} 字节）：{e}")
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise SystemExit(f"[!] {path.name} 结构不对：缺少 files 数组")
    print(f"  清单自检通过：{len(data['files'])} 个条目")


def inline_cover(path: pathlib.Path, max_w: int = 1200, quality: int = 82):
    """封面转成「适合网页内嵌」的 JPEG 字节。
    内嵌的图片会直接计入 index.html 体积，而首屏时间几乎等于这个体积，
    所以超过 1200px 宽就等比缩小、并按 quality 重压；失败时退回原图。"""
    raw = path.read_bytes()
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = img.size
        need = w > max_w
        if need:
            img = img.resize((max_w, round(h * max_w / w)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        out = buf.getvalue()
        if len(out) < len(raw):
            note = (f"已压缩 {len(raw):,} -> {len(out):,} bytes"
                    + (f"（{w}px 缩到 {max_w}px q{quality}）" if need else f"（q{quality}）"))
            return out, note
    except Exception as e:
        print(f"  [提示] 封面压缩跳过（{type(e).__name__}: {e}），用原图")
    return raw, f"原图 {len(raw):,} bytes"


def collect():
    TEXTS.mkdir(parents=True, exist_ok=True)
    names = sorted((p.name for p in TEXTS.iterdir()
                    if p.is_file() and p.suffix.lower() in EXTS and p.name not in SKIP),
                   key=natural_key)
    return [{"name": n, "content": read_text(TEXTS / n)} for n in names]


def main():
    check_manifest(TEXTS / "index.json")        # 先体检
    files = collect()

    # 清单：给 GitHub Pages 上的实时读取用（先写临时文件再替换，避免中途失败留下半截文件）
    manifest = {"files": [{"name": f["name"], "size": (TEXTS / f["name"]).stat().st_size}
                          for f in files]}
    mani_path = TEXTS / "index.json"
    mani_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    mani_changed = (not mani_path.is_file()) or mani_path.read_text(encoding="utf-8") != mani_text
    if mani_changed:
        tmp = mani_path.with_suffix(".json.tmp")
        tmp.write_text(mani_text, encoding="utf-8", newline="\n")
        tmp.replace(mani_path)

    # 离线快照：base64(JSON)，base64 里不会出现 </script>，塞进页面绝对安全
    snap = base64.b64encode(json.dumps(files, ensure_ascii=False).encode("utf-8")).decode("ascii")

    # 封面内嵌成 data URI；顺带压缩一下（它是 index.html 体积的大头，直接影响首屏时间）
    cover_bytes, cover_note = inline_cover(COVER)
    cover = "data:image/jpeg;base64," + base64.b64encode(cover_bytes).decode("ascii")

    # 标签页图标：内嵌 data URI，双击打开也能显示（缺失则跳过，不报错）
    def data_uri(path, mime):
        p = BASE / path
        if not p.is_file():
            print(f"  [提示] 没有 {path}，图标位置留空（可用 tools/make_favicon.py 生成）")
            return ""
        return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")

    page = (TPL.read_text(encoding="utf-8")
            .replace("GITHUB_REPO", REPO)
            .replace("FAVICON_32_URI", data_uri("favicon-32.png", "image/png"))
            .replace("FAVICON_180_URI", data_uri("apple-touch-icon.png", "image/png"))
            .replace("SNAPSHOT_B64", snap)
            .replace("COVER_DATA_URI", cover))
    OUT.write_text(page, encoding="utf-8", newline="\n")

    print(f"texts/ 里的文件（{len(files)} 个）：")
    for f in files:
        print(f"  + {f['name']:<26} {len(f['content'].splitlines()):>4} 行  {len(f['content']):>7} 字符")
    if not files:
        print("  (空) —— 丢几个 .txt 进 texts/ 再跑一次")

    print(f"\nindex.html        {OUT.stat().st_size:>9,} bytes   （含离线快照，双击即可看）")
    print(f"  封面内嵌        {cover_note}")
    print(f"texts/index.json  {mani_path.stat().st_size:>9,} bytes   （{'已更新' if mani_changed else '无变化'}）")
    bgm = BASE / "bgm.mp3"
    print(f"bgm.mp3           " + (f"{bgm.stat().st_size:>9,} bytes   （背景音乐，不点播放就不下载）"
                                   if bgm.is_file() else "   缺失 —— 播放按钮会提示加载失败"))
    print("\n部署后页面会自动改用实时的 texts/ 文件夹；本地双击则用内嵌快照。")


if __name__ == "__main__":
    sys.exit(main())
