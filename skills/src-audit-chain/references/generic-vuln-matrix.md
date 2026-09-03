# 通用漏洞矩阵（代码审计主清单）

按 **出现频率 × 影响** 排序。每个项目先勾选本表，再深挖产品逻辑。

## A. 控制面（最先查）

| ID | 通用类 | CWE | 源码信号 | 确认条件 | 典型影响 |
|---|---|---|---|---|---|
| G01 | 缺失身份认证 | 306 | 无 login / before_request / middleware / API key 校验 | 管理 API 匿名可达 | 直接后台 |
| G02 | 失效的访问控制 | 284 | 有登录但管理/危险接口无角色校验 | 低权限可调高权限接口 | 越权打后台 |
| G03 | 危险绑定 | 668 | `0.0.0.0` / `::` 监听管理端口 | 默认配置即全网卡 | 暴露面放大 |
| G04 | 过宽 CORS | 942 | `Access-Control-Allow-Origin: *` + 凭证或管理 API | 任意源可调 | 浏览器侧滥用 |
| G05 | 硬编码密钥 | 798 | `SECRET_KEY` / 密码 / token 写死 | 仓库或配置可见 | 会话伪造/凭据复用 |

## B. 数据出站 / 入站

| ID | 通用类 | CWE | 源码信号 | 确认条件 | 典型影响 |
|---|---|---|---|---|---|
| G10 | SSRF | 918 | `requests`/`httpx`/`urllib` 使用用户 URL | 无内网/元数据拒绝；或可回显 | 打内网/本机管理面 |
| G11 | Full-read SSRF | 918 | 响应 body/headers 返回客户端 | 同上 + 回显 | 读内网响应 |
| G12 | 开放重定向 | 601 | 跳转目标用户可控 | 无 allowlist | 钓鱼/token 泄露 |
| G13 | 任意文件读 | 22 | `send_file`/`open` 拼接用户路径 | `../` 或绝对路径成功 | 读配置/密钥 |
| G14 | 任意文件写/删 | 22/73 | 上传、解压、`rmtree(用户名)` | 路径未规范化 | 落盘 webshell/破坏 |

## C. 注入与执行

| ID | 通用类 | CWE | 源码信号 | 确认条件 | 典型影响 |
|---|---|---|---|---|---|
| G20 | OS 命令注入 | 78 | `os.system`/`Popen`/`shell=True` + 用户输入 | 元字符进入 shell | RCE |
| G21 | 间接 RCE | 78 | 配置可写可执行路径 + 启动接口 | 路径存在且被 Popen | RCE（有条件） |
| G22 | SSTI | 94 | `render_template_string(用户)` | 表达式执行 | RCE |
| G23 | 反序列化 | 502 | `pickle`/`yaml.load`/`ObjectInputStream` | 用户数据进 sink | RCE |
| G24 | SQLi | 89 | 字符串拼 SQL | 可改变查询逻辑 | 数据/后台 |
| G25 | NoSQLi / 操作符注入 | 943 | 用户 JSON 直接进 query | `$where`/`$gt` 等 | 绕过/拖库 |
| G26 | ReDoS | 1333 | 用户输入进 `$regex`/复杂正则 | 可构造恶正则 | DoS |

## D. 前端 / 会话

| ID | 通用类 | CWE | 源码信号 | 确认条件 | 典型影响 |
|---|---|---|---|---|---|
| G30 | 反射 XSS | 79 | 输入进 HTML/JS 未编码 | 即时回显可执行 | 会话/操作 |
| G31 | 存储 XSS | 79 | 入库字段前端 `.html()`/`data-*=${}` | 再次打开可执行 | 打管理员 |
| G32 | 属性注入 | 79 | 只 escape 文本、不 escape 属性 | `"` 破属性 | XSS |
| G33 | CSRF | 352 | 改状态接口无 token/SameSite | 跨站可触发 | 借管理员操作 |

## E. 配置与密钥

| ID | 通用类 | CWE | 源码信号 | 确认条件 | 典型影响 |
|---|---|---|---|---|---|
| G40 | 敏感信息泄露 | 200 | `/config` `/debug` `/actuator` 匿名 | 回传密钥 | 扩权 |
| G41 | 配置可写 | 732 | POST 写配置无鉴权 | 可改路径/代理/密钥 | 投毒/RCE 前置 |
| G42 | 明文存储密码 | 312 | 配置/日志明文 password | 可读 | 横向 |

## 判定规则

```
Confirmed  = 控制缺失 + source→sink 代码闭环 +（可选）利用条件满足
Likely     = 控制缺失 + sink 明确，差一步动态或落盘条件
Info       = 坏味道明确但难利用或仅本地
Negated    = 框架/中间件已防护，或 sink 不可达
```

## 快速 grep 种子（按语言增补）

```text
# Auth absence / bind
0.0.0.0 | before_request | login_required | cors_allowed_origins

# SSRF
requests.(get|post|request) | httpx. | urlopen | urllib.request

# RCE
os.system | subprocess | Popen | shell=True | eval( | exec(

# XSS frontend
.innerHTML | .html( | dangerouslySetInnerHTML | data-\w+=\$\{

# Secrets
SECRET_KEY | API_KEY | password\s*=
```

## 输出表格式

```markdown
| ID | 类别 | CWE | 位置 | 状态 | 打后台关系 | 修复 |
|----|------|-----|------|------|------------|------|
| G01 | 缺失认证 | 306 | app.py | Confirmed | Chain A | 全局鉴权+本机绑定 |
```
