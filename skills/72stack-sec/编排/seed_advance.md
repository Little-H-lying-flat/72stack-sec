# 种子推进（seed_advance）

> 治 **席空待补给**：watchdog 收尸后 leftover 业务 pending 空，却不 FOFA 续页/下种子。  
> 接在 `seat_watchdog --apply` 之后（默认 `--auto-fofa`）。

## 触发条件

```text
seats doing == 0
且 leftover 业务 pending < min（默认 1）
且 种子队列有 doing 种子
→ FOFA domain=种子 page=状态页+1
→ 洗 NEW 业务 host 追加 leftover pending
→ chain seat_watchdog 填席出 batch
→ 连续 0 NEW 达 streak（默认 3）→ vacuum → NEXT: 下种子
```

## 命令

```bat
python seed_advance.py --task-root "D:\SRC挖洞\小红书_V3_SRC挖洞" --dry-run
python seed_advance.py --task-root "…" --apply --chain-watchdog
python seat_watchdog.py --task-root "…" --apply
rem 默认已 auto-fofa；关闭：--no-auto-fofa
```

状态文件：`编排/fofa_state.json`（page / zero_new_streak / vacuum）。

## 噪音过滤

默认不入业务 pending：`.qa.` `.tst.` `.io.` `sup.io` `localhost` `cdn` 等（见脚本 NOISE_HOST）。

## 禁止

执行腿禁止跑。不打印 FOFA key。不替代股权闸（NEW 仍要主控抽查）。
