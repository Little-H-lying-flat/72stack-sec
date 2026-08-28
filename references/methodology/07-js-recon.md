# JS 侦察 — 前端资产里的 endpoint 与密钥 `js-recon`

> 定位:现代 SPA(React/Vue/Next/Nuxt)的 bundle 是 **endpoint、隐藏路由、密钥的第一来源**。前端的"隐藏"只是 UI 隐藏——路由/接口/权限判断全在 JS 里裸奔。
> 铁律(呼应 06 §5):**前端可见 ≠ 后端允许**。JS 里发现的每个 endpoint 都必须按匿名/低权/越权三层验证后端行为,前端校验是 theater。

---

## 1. JS 资产收集

| 来源 | 手法 |
|---|---|
| 页面内 | 所有 `<script src>`、`link rel=preload/prefetch`、动态 import() |
| 爬取 | katana / hakrawler / gospider 对目标域爬 js;`-js` 类参数保留 js 链接 |
| 历史 | waybackurls / gau 拉**历史快照里的 js**——下线页面的 js 指向未下线的接口,经典金矿 |
| Dork | `site:target.com ext:js` / `site:target.com inurl:.js` |
| 子域联动 | httpx 探活的子域全部过一遍 js 提取(每个 SPA 都是一座矿) |

## 2. Source Map 还原(生产环境忘删 .map = 直接读源码)

```
1. 看 js 尾部: //# sourceMappingURL=app.js.map
2. 直接探测: 对每个 js 加 .map 后缀请求(200 即中)
3. 还原: shuji / unmap / sourcemapper → 还原出原始目录结构与源文件
4. 价值排序: src/api/ 目录(全部接口定义) > src/store(状态与权限逻辑) > src/config(环境配置) > 注释
```

还原出的 api 目录=完整的接口清单,比任何正则都全。**报告注意**:source map 暴露本身多数平台按低危收,但其导出的接口/密钥按实际影响定级。

## 3. Webpack Chunk 遍历

- 命名规律:`app.[hash].js`、`{N}.{hash}.chunk.js`、`static/js/{N}.{hash}.chunk.js`
- 遍历法:从 runtime(manifest)chunk 里拿全量 chunk 映射;或对 chunk id 做数字递增尝试(`1.js`~`500.js`,配合 hash 才有效,无 hash 直接试)
- 框架数据负载:`__NEXT_DATA__`(Next)、`__NUXT__`(Nuxt)——页面级 props 里常有 API base、用户上下文、内部配置
- 路由提取:react-router/vue-router 的路由表是明文数组——**admin/dashboard/internal 等隐藏路由**直接从路由表读,然后逐个验证后端鉴权(路由隐藏≠授权)

## 4. Endpoint / 密钥正则清单(对 bundle 直接 grep)

```
# endpoint
/api/[a-zA-Z0-9_/-]+      fetch\(["']       axios\.(get|post|put|delete)
baseURL                    graphql           /v[0-9]/[a-z]+/

# 云凭据(对应 11-cloud.md 接管链)
AKIA[0-9A-Z]{16}                      # AWS
LTAI[0-9A-Za-z]{12,}                  # 阿里云 AK
AKID[0-9A-Za-z]{13,}                  # 腾讯云
AIza[0-9A-Za-z_-]{35}                 # Google API key
sk-[a-zA-Z0-9]{20,}                   # OpenAI 风格 key
ghp_[A-Za-z0-9]{36} / github_pat_     # GitHub PAT
xox[baprs]-                           # Slack token

# 其他敏感物
eyJ[A-Za-z0-9_-]{10,}\.eyJ            # JWT 硬编码
(25[0-5]|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)  # 内网 IP
https?://[a-z-]+\.(internal|local|corp)[^"']*   # 内部域名
password|secret|token|api[_-]?key      # 配置字段名(再人工核)
```

工具化:gitleaks/trufflehog 思路直接对 bundle 目录跑;LLM 分诊(06 §5)适合做"端点聚类+可疑度排序",人只看 top。

## 5. 第三方与全局配置

- CDN 上的老组件:jQuery <3.5(xss)、老版本 moment/lodash(原型链)——`retire.js` / 指纹比对
- `window.config` / `window.__INITIAL_STATE__`:全局配置常塞内部 RPC 地址、功能开关、灰度配置
- 上传/预览组件的 bucket 地址:转 `11-cloud.md` 的 `cn-object-storage` 打对象存储

## 6. 后端验证矩阵(js-recon 的收口)

| JS 里的发现 | 验证动作 | 出口 |
|---|---|---|
| 隐藏路由 /admin | 匿名直访 + 低权账户访问,看**后端**返回 | 前端隐藏但后端拦→信息泄露(低);后端放行→越权(P1) |
| 未文档化 endpoint | 匿名 OPTIONS/GET 探测 → 带低权 token 测 | 按 BOLA/未授权定级,进 `api-rest/` |
| 硬编码密钥 | 验证有效性(最小请求,如 sts get-caller-identity) | 有效→按云凭据接管链(11-cloud.md) |
| source map | 还原→接口清单回填第 1-3 步 | 循环放大,直到无新 endpoint |

## 7. 流水线示例

```
katana -u https://target -d 3 -jc | grep -oE 'https?://[^" ]+\.js' | sort -u > js.txt
while read u; do curl -s "$u" -o "js/$(echo $u | md5sum | cut -c1-8).js"; done < js.txt
grep -rhoE '(AKIA[0-9A-Z]{16}|LTAI[0-9A-Za-z]{12,}|/api/[a-zA-Z0-9_/-]+)' js/ | sort -u
# → 人工/LLM 分诊 → 后端验证矩阵
```

来源:公开常用手法整理(katana/gau/waybackurls 等 README、hakrawler、各 JS 侦察公开文章),无未披露内容。
