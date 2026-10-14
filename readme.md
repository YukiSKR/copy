# 站点:https://yukiskr.github.io/copy/
# 文本切换台 · 纯前端版（部署到 GitHub Pages）

一个纯前端小站：读取仓库 `texts/` 文件夹里的文本，标签页切换，一键复制并弹出提示。
**没有后端、没有服务器、没有构建服务** —— `index.html` 一个文件就是整个网站。
而且 `index.html` 里自带一份**离线快照**：双击就能看能复制，不需要任何服务。

加新文本：往 `texts/` 里丢一个 `.txt` → 提交推送 → 刷新页面就有新标签。

---

## 一、文件说明

```
copy-card/
├─ index.html          ← 整个网站（部署用，必提交）
├─ cover.jpg           ← 封面插画（打包时内联进 index.html，留作备份）
├─ template.html       ← 页面模板（改样式/文案改这里）
├─ build.py            ← 把 template + cover + texts/index.json 组装成 index.html
├─ texts/              ← ★ 文本都放这里
│  ├─ index.json       ← 文件清单（自动生成，别手改）
│  ├─ copy.txt
│  └─ 使用说明.txt
├─ .github/workflows/update-manifest.yml  ← push 后自动更新清单，无需本地 Python
├─ .nojekyll           ← 让 Pages 原样提供文件
├─ tools/e2e.js        ← 端到端自检（可选，开发用）
├─ verify.py           ← 打包自检（可选，开发用）
└─ 部署说明.md          ← 本文件
```

> 需要提交的只有：`index.html`、`texts/`、`.nojekyll`、`.github/`。
> `build.py`、`template.html`、`verify.py`、`tools/` 是开发用的，想留就留，不影响部署。

## 二、双击就能看（离线快照）+ 部署后自动实时

`index.html` 里有两套取内容的路径，页面会自己选：

| 打开方式 | 行为 |
| --- | --- |
| **双击 index.html**（`file://`） | 浏览器禁止读本地文件 → 自动用 **index.html 自带的离线快照**，标签带「📦 ·快照」，页脚标注「离线快照」。**能看、能切、能复制，不需要任何服务** |
| **部署后访问网址**（GitHub Pages） | 优先 `fetch('texts/index.json')` + 逐个读 `texts/文件名`，页脚显示「数据来源：texts/清单」。**往文件夹丢新 txt 就自动出现** |

> 想让「双击版本」也带上最新文本，本地跑一次 `python build.py` 即可（它把 `texts/` 的内容打进 `index.html`）。
> 部署时 Action 会自动跑这一步，所以你只管推文件。

## 三、部署（3 步）

1. GitHub 新建仓库（如 `txt-copy`），**Public**（私有仓库要付费版才能开 Pages）
2. 本地在该文件夹里执行：

```bat
git init
git add .
git commit -m "feat: 文本切换台"
git branch -M main
git remote add origin https://github.com/你的用户名/txt-copy.git
git push -u origin main
```

3. 仓库 **Settings → Pages** → Source 选 `Deploy from a branch` → Branch 选 `main` / 目录 `/ (root)` → 保存。

约 1~2 分钟后访问：

```
https://你的用户名.github.io/txt-copy/
```

以后改了页面或文本，`git push` 即可，Pages 会自动重新发布。

## 四、日常加文本

```bat
copy 新脚本.txt copy-card\texts\
cd copy-card
git add texts
git commit -m "add: 新脚本"
git push
```

- 仓库里的 **Action 会自动重新生成 `texts/index.json`** 并提交回来（约 20~40 秒，仓库 Actions 页能看到绿勾）
- 等它跑完，刷新网页就有新标签
- 页面上的 **「🔄 重新读取」** 按钮 = 重新拉一次清单，不用按 F5

> 完全不用在本地装 Python：清单交给 Action 维护就行。
> 如果你本地有 Python，也可以跑 `python build.py` 自己更新清单，效果一样。

## 五、它是怎么“读到文件夹”的

GitHub Pages 是纯静态托管，**没有后端、也不能列出目录**，浏览器无法自己知道 `texts/` 里有什么。做法：

1. `texts/index.json` 清单列出文件名（Action 自动维护）
2. 页面 `fetch('texts/index.json')` → 再逐个 `fetch('texts/文件名')` 取内容
3. 万一清单缺失或没更新，页面还会**回退探测**常见文件名（`copy.txt`、`text.txt`、`readme.md`…），不会整页空白

所以唯一要注意的：**新增文件后清单要跟着更新**（交给 Action 就行）。

## 六、常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| 双击打开时页脚写着「离线快照」 | 正常：`file://` 下浏览器禁止读本地文件，页面用了 index.html 自带的快照。想要最新内容就跑 `python build.py` |
| 双击打开提示「没能读取 texts/ 且没有离线快照」 | 这份 index.html 是没打包过的模板产物 → 跑一次 `python build.py` |
| 新加的 txt 在网址上不出现 | Action 还没跑完（看 Actions 绿勾）；点「🔄 重新读取」；或检查 `texts/index.json` 是否已更新 |
| 页面 404 | Settings → Pages 的分支/目录选错，或还没发布完（等 1~2 分钟） |
| 中文乱码 | 文本请存成 **UTF-8** 编码 |
| 想放进仓库子目录 | 直接把整个文件夹推上去即可，页面用相对路径 `texts/`，无需改代码 |
| 想换封面 | 用新图替换 `cover.jpg`（1280×904 左右的插画），跑一次 `python build.py` 重新内联 |
| 默认打开的是哪个文件 | 按文件名排序（数字感知）后的第一个，所以 `copy.txt` 排在 `使用说明.txt` 前面 |

## 七、页面功能

- **标签切换**：读取 `texts/` 里所有文本，按文件名排序（数字感知，text2 在 text10 前）
- **一键复制**：主按钮 / 代码框右下角迷你按钮；成功时星星四散、按钮变绿、弹出「🎉 复制成功」对话框（显示是哪个文件）
- **单击正文全选**，方便手动 Ctrl+C
- **拖 txt 进页面** 或点 **「＋ 添加 txt」**：临时加标签，存在浏览器本地，刷新不丢（`×` 可删）——适合临时看一眼、不想进仓库的情况
