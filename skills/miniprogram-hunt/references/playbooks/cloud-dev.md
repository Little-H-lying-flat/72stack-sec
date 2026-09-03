# 云开发（wx.cloud）安全 Playbook

> 小程序特有攻击面：云函数、云数据库、云存储、云环境 ID。本地静态只能看到调用代码，**实际风险取决于云端权限规则配置**——结论必须经动态验证，无证据不下结论。

## 攻击面识别

```powershell
# 云环境 ID + 云函数调用 + 集合操作
Select-String -Path "$unpackDir\**\*.js" -Pattern 'wx\.cloud\.init|wx\.cloud\.callFunction|\.collection\(|wx\.cloud\.(uploadFile|downloadFile|getTempFileURL)' -AllMatches |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

**识别信号**：
- `wx.cloud.init({env: 'cloud1-xxxx'})` → **云环境 ID 泄露**（High：攻击面入口）
- `wx.cloud.callFunction({name: 'getUser', data: {...}})` → 云函数名清单
- `db.collection('orders').where({...}).get()` → 集合名 + 查询条件
- `wx.cloud.uploadFile({cloudPath: ...})` / `getTempFileURL({fileList: ...})` → 云存储路径

**MCP 加速**：`miniapp_cloud_scan(appid)` 一键静态提取云函数名+集合名；动态验证见 Phase 4.1（`call_cloud` 直调 / `cloud_captures` hook 捕获真实参数）。

## 漏洞挖掘路径

### 路径 A：云函数未授权 / 鉴权缺失

**source**：静态提取的云函数名 + 调用参数结构
**sink**：云函数内部未校验 `OPENID` 归属，直接按入参查询/写库

**测试**：
1. 无参直调：`call_cloud(name)` 不带 data，观察返回（报错信息常泄露参数结构/内部逻辑）
2. 构造最小参数调用，先只读函数（get/list/detail/query 类）
3. 换参越权：把入参中的 `openid`/`userId`/`_id` 换成他人值，返回他人数据 → 确认
4. 写函数（add/update/delete 类）遵守最小伤害：**只添加后立刻删除自己刚加的那条**，禁改/删他人现存数据，禁批量

**典型漏洞特征**（静态线索）：
- 函数名含 `admin`/`manage`/`getAll`/`export`/`debug`
- 入参直接进 `db.collection(x).where({_id: event.id})`，无 `OPENID` 归属过滤
- 前端传 `openid` 作为查询参数（正常应由云端从上下文取）→ 大概率信任前端身份

### 路径 B：云数据库权限规则缺陷

**source**：`db.collection()` 前端直接查询的集合名
**sink**：集合权限规则设为「所有用户可读」

**测试**：
1. 从前端代码还原前端侧直接 `where({}).get()` 的集合（无条件全量查询是明显信号）
2. 小程序端以普通用户身份实测能否读出他人数据（前端直查受权限规则约束，规则紧则假警）
3. 前端直查 + 云函数代查是两条不同权限通道，**分开测**：云函数内 `db` 默认绕过小程序端权限规则

### 路径 C：云存储未授权访问

**source**：`cloudPath` 拼接逻辑、`fileID` 来源
**sink**：存储权限「所有用户可读」+ 路径可枚举

**测试**：
1. 提取 cloudPath 模板（如 `user/{openid}/avatar.png`），测路径可否改写覆盖/遍历
2. `getTempFileURL` 对他人 fileID 换 id 取临时链接，能取回他人文件 → 确认
3. 上传口测 cloudPath 可控（`../` / 绝对路径 / 覆盖他人文件名——**只测自己名下，不覆盖他人现存文件**）

## 验证标准

- **云函数越权**：换 id 后返回他人真实数据（非空壳/非脱敏），截图记录入参与返回
- **未授权调用**：无登录态/无参数直调返回真实业务数据
- **存储越权**：换 fileID 实际取回他人文件内容
- 诚实标注：云端权限规则无法本地确认的，一律标「需后端验证」，不许凭前端代码断言

## 纪律（叠加 zsec 硬约束）

- 云函数直调 = 直接打生产后端：只读优先、单次不批量、写操作加后删、全程留证据
- `env` ID / 云函数名清单属敏感信息，写报告时按 vuln-report-format「密钥放哪」处理
