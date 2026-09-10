# 72stack-sec 命名对照

更新日期：2026-09-10

## 一句话

**对外叫 72stack-sec；本机 Grok 实战目录叫 `skill`。**

## 对照表

| 场景 | 正确引用 | 错误用法 |
|------|----------|----------|
| GitHub 仓库 | `Little-H-lying-flat/72stack-sec` | 把仓库名当成 `~/.grok/skills/` 下文件夹 |
| 仓库内主 skill | `skills/72stack-sec/` | 与本机目录强制同名（当前本机仍为 `skill`） |
| Grok 运行时 | `~/.grok/skills/skill` | `~/.grok/skills/72stack-sec`（除非你已改安装名） |
| 线程/开场禁旁路 | 不要走 `/hack`、`src-hunter`、另一套未安装路径 | 把「禁 72stack」理解成禁止对外品牌名 |
| 调度正文 | `主控调度.md` | 在薄 `SKILL.md` 里找双轨长文 |

## 同步建议

1. **短期**：保持本机目录名 `skill`（少动安装与既有任务指针）；仓库与 README 统一讲 72stack-sec。  
2. **中期（可选）**：增加安装说明「克隆后拷贝/链接为 `~/.grok/skills/skill`」，或提供 `install.ps1` 做 junction。  
3. **长期（可选）**：若 Grok 允许多 skill 名，再评估本机改名为 `72stack-sec`，并批量替换开场提示词路径。

## 与线程必读的关系

`线程必读.md` 中「禁 72stack」= **禁止 Agent 改用未安装的旁路 skill 名/路径**，避免和 `/hack`、`src-hunter` 混用。  
对外文档、简历、仓库星标页继续使用 **72stack-sec**。


## 同步方向（2026-09-10）

以本机实战目录 `~/.grok/skills/skill` 为真源，覆盖仓库 `skills/72stack-sec/`。  
安装回本机时仍落到 `~/.grok/skills/skill`（见该目录 `README.md`）。
