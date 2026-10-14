# -*- coding: utf-8 -*-
"""
把「远端最新文件树」和「本次改动后的文件树」合并成一个新 tree 清单。

为什么需要它：GitHub 的 tree 是「整树替换」——如果把只含部分文件的 tree 提交上去，
其余文件会被删掉。这个脚本保证：只覆盖本次真正改动的文件（index.html 与
texts/index.json），仓库里其他文件（例如你在网页上直接上传的 txt）原样保留。

用法（在 workflow 里）：
    这是由 .github/workflows/update-manifest.yml 调用的，见 tools/merge_tree.py
"""

import pathlib
import subprocess
import sys
import tempfile

# 这些路径用「本地新版本」覆盖远端；其余一律沿用远端
OVERRIDE = ("index.html", "texts/index.json")
OUT = pathlib.Path(tempfile.gettempdir()) / "merged.txt"     # Windows/Linux 都可用


def ls_tree(rev: str) -> dict:
    """返回 {路径: (mode, type, sha)}，路径按 UTF-8 原样解码"""
    out = subprocess.run(["git", "ls-tree", "-r", "-z", rev],
                         capture_output=True, check=True).stdout
    entries = {}
    for item in out.split(b"\0"):
        if not item.strip():
            continue
        meta, path = item.split(b"\t", 1)
        mode, typ, sha = meta.decode().split()
        entries[path.decode("utf-8")] = (mode, typ, sha)
    return entries


def main() -> int:
    remote_rev = sys.argv[1] if len(sys.argv) > 1 else "FETCH_HEAD"
    local_rev = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    out = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else OUT

    remote = ls_tree(remote_rev)
    local = ls_tree(local_rev)
    before = len(remote)

    changed = []
    for name in OVERRIDE:
        if name in local and remote.get(name) != local[name]:
            changed.append(name)
        if name in local:
            remote[name] = local[name]

    lines = [f"{m} {t} {s}\t{n}" for n, (m, t, s) in sorted(remote.items(), key=lambda kv: kv[0])]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"远端文件 {before} 个 / 本地文件 {len(local)} 个")
    print("覆盖的文件：" + ("、".join(changed) if changed else "（无变化）"))
    print(f"合并后 {len(remote)} 个文件 -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
