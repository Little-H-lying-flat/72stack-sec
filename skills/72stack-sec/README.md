# 72stack-sec（Grok / Agent Skill）

本目录是 **72stack-sec** 的主技能源码。

## 安装到本机 Grok

拷贝或 junction 到：

```text
~/.grok/skills/skill
```

（文件夹名保持 `skill` 是当前 Grok 实战约定；产品名仍是 72stack-sec。详见仓库根目录 `NAMING.md`。）

## 开场

1. `SKILL.md`（红线 + 指针）
2. `主控调度.md`（双轨 / 进号 / spawn）
3. `开场提示词.md` / `线程必读.md`

covered 前：

```bash
python scripts/suspects_coverage_check.py --host-dir "{dig}/{host}"
```

仓库根 README 有产品叙事；本文件只管安装与入口。