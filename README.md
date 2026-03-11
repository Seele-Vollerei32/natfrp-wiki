# Sakura Frp 帮助文档

这是 [SakuraFrp](https://www.natfrp.com/) 的官方帮助文档仓库。

## 关于

为了提供较好的在线阅读体验，我们将本应放在 `README.md` 的内容移动到了 `about.md` 和 `index.md` 中。

请参阅 [关于](https://doc.natfrp.com/about.html) 页面和 [帮助文档首页](https://doc.natfrp.com/)。

## 贡献

欢迎您参与本文档的编写、修订工作，在提交 PR 前请参阅 [文档格式约定](https://doc.natfrp.com/style.html) 一节。

## 机器人语料库

本仓库提供一个从 Wiki 文档自动生成的机器人关键词自动回复语料库，存储于 [`corpus.json`](./corpus.json)。

### 语料格式

每条语料包含以下字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 唯一标识符（来自 Markdown 锚点或自动生成） |
| `question` | 问题/标题文本 |
| `keywords` | 关键词列表，用于机器人匹配用户输入 |
| `answer` | 回答内容（纯文本，已去除 Markdown 格式） |
| `url` | 对应的在线文档链接（可引导用户查看完整内容） |
| `category` | 分类（如 `常见问题`、`frpc 客户端`、`应用配置指南` 等） |

### 更新语料库

每次 Wiki 内容更新后，可以重新运行生成脚本来更新语料库：

```bash
python3 scripts/generate_corpus.py
```

也可以指定输出路径：

```bash
python3 scripts/generate_corpus.py --output path/to/corpus.json
```
