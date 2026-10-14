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


def natural_key(name: str):
    """数字感知排序，和页面里的 naturalCompare 保持一致"""
    return [int(p) if p.isdigit() else p.lower() for p in re.findall(r"\d+|\D+", name.lower())]


def read_text(p: pathlib.Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return p.read_text(encoding=enc).replace("\r\n", "\n").rstrip("\n")
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").rstrip("\n")


def collect():
    TEXTS.mkdir(parents=True, exist_ok=True)
    names = sorted((p.name for p in TEXTS.iterdir()
                    if p.is_file() and p.suffix.lower() in EXTS and p.name not in SKIP),
                   key=natural_key)
    return [{"name": n, "content": read_text(TEXTS / n)} for n in names]


def main():
    files = collect()

    # 清单：给 GitHub Pages 上的实时读取用
    manifest = {"files": [{"name": f["name"], "size": (TEXTS / f["name"]).stat().st_size}
                          for f in files]}
    mani_path = TEXTS / "index.json"
    mani_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    mani_changed = (not mani_path.is_file()) or mani_path.read_text(encoding="utf-8") != mani_text
    if mani_changed:
        mani_path.write_text(mani_text, encoding="utf-8", newline="\n")

    # 离线快照：base64(JSON)，base64 里不会出现 </script>，塞进页面绝对安全
    snap = base64.b64encode(json.dumps(files, ensure_ascii=False).encode("utf-8")).decode("ascii")

    cover = "data:image/jpeg;base64," + base64.b64encode(COVER.read_bytes()).decode("ascii")

    # 标签页图标：内嵌 data URI，双击打开也能显示（缺失则跳过，不报错）
    def data_uri(path, mime):
        p = BASE / path
        if not p.is_file():
            print(f"  [提示] 没有 {path}，图标位置留空（可用 tools/make_favicon.py 生成）")
            return ""
        return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")

    page = (TPL.read_text(encoding="utf-8")
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
    print(f"texts/index.json  {mani_path.stat().st_size:>9,} bytes   （{'已更新' if mani_changed else '无变化'}）")
    print("\n部署后页面会自动改用实时的 texts/ 文件夹；本地双击则用内嵌快照。")


if __name__ == "__main__":
    sys.exit(main())
