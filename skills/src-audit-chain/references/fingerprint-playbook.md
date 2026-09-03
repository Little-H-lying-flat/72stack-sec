# 指纹与 FOFA 语法手册

## 提取顺序

1. `templates` / 前端入口 `<title>`
2. Logo 文案、产品中文全称、独特菜单
3. 默认端口（config / docker-compose / app.run）
4. 独特 API（如 `/api/tools/replay`）
5. 静态资源特征路径、favicon
6. 硬编码产品字符串（注意误报）

## 语法质量

| 等级 | 形态 | 用途 |
|---|---|---|
| 高 | `title="完整产品标题"` | 主查询、计案例 |
| 中 | `body=A && body=B` 双锚点 | 主/备 |
| 低 | `title="短名"` | **仅噪声对照，不计产品案例** |
| 辅 | `port="N"` | 必须与高/中语法 AND |

## 去重

- 首选 `ip:port`
- 其次独立 host
- CDN 同 IP 多 host 需抽样 title
- 记录查询时间与语法

## 误报纪律

- 同名短词（Facai、Admin、Panel）必须二次校验 title/body
- NAS、博彩、招商站等与安全产品同名时 **剔除**
- 精确语法 0 命中是合法结论

## 多引擎

| FOFA | Hunter | Quake |
|---|---|---|
| `title="X"` | `web.title="X"` | `title:"X"` |
| `body="X"` | `web.body="X"` | `body:"X"` |
| `port="N"` | `ip.port="N"` | `port:N` |
| `icon_hash="H"` | `web.icon="H"` | `favicon:"H"` |
