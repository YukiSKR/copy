# -*- coding: utf-8 -*-
"""
【已弃用 · 请勿在 workflow 里使用】

这是早期「手工拼 git tree」的方案，实测行不通：
`git mktree` 只接受"一层"条目，路径里带 `/` 会直接报
`fatal: path xxx contains slash`（加 `-z` 也一样，Git 2.55 实测）。
而手搓嵌套 tree 又容易出错。

现在 workflow 用的是更笨但可靠的做法（见 .github/workflows/update-manifest.yml）：
    ① git fetch origin main --force          # 对齐远端最新
    ② git reset --mixed FETCH_HEAD           # 索引 = 远端状态（其他文件天然保留）
    ③ git add index.html texts/index.json    # 只覆盖本次真正改动的文件
    ④ git write-tree / git commit-tree / git push

本文件保留仅作记录，防止以后再走这条路。
"""

import pathlib
import subprocess
import sys
import tempfile

# 这些路径用「本地新版本」覆盖远端；其余一律沿用远端
OVERRIDE = ("index.html", "texts/index.json")


def ls_tree(rev: str) -> dict:
    """{路径: (mode, type, sha)}，用 -z 拿到未转义的真实路径"""
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
    out = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 \
        else pathlib.Path(tempfile.gettempdir()) / "merged.bin"

    remote = ls_tree(remote_rev)
    local = ls_tree(local_rev)
    before = len(remote)

    changed = []
    for name in OVERRIDE:
        if name in local:
            if remote.get(name) != local[name]:
                changed.append(name)
            remote[name] = local[name]

    # -z 格式：<mode> SP <type> SP <sha> TAB <path> NUL
    data = b"".join(
        f"{m} {t} {s}\t{n}".encode("utf-8") + b"\0"
        for n, (m, t, s) in sorted(remote.items(), key=lambda kv: kv[0])
    )
    out.write_bytes(data)

    print(f"远端文件 {before} 个 / 本地文件 {len(local)} 个")
    print("覆盖的文件：" + ("、".join(changed) if changed else "（无变化）"))
    print(f"合并后 {len(remote)} 个文件 -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
