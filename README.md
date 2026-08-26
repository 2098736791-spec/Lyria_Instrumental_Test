# 纯音乐按钮 prompt 服务

> 一个可独立部署的后端组件:**用户输入 + 纯音乐开关 → 最终 Lyria prompt**。
> 生产路径零 key 零依赖毫秒级返回;真实 Lyria 生成是可选的试用能力。
> 实验依据(100% 服从实测):`../experiments/2026-08-no-vocals/`(报告在 `deliverables/`)。

## ⚡ 接口速查(入参 / 出参 / 默认值)——最重要的一节

**`POST /prompt`**,请求体 JSON。

> ### ⚠️ `instrumental` 必填,没有默认值!
> **请求里不带 `instrumental` 字段 → 直接 422 拒绝,服务不会替你猜。**
> 必须每次显式传:纯音乐按钮按下传 `true`,没按下传 `false`。
> (另一个必填是 `user_input`;其余三个字段都有默认,不传也行。)

### 入参(5 个字段)

| 字段 | 必填 | 不传时的默认 | 说明 |
|---|---|---|---|
| **`instrumental`** | **✅ 必填** | **无!漏传即 422** | 纯音乐开关。`true` = 加工出纯音乐 prompt;`false` = 用户输入**原样透传** |
| **`user_input`** | **✅ 必填** | 无,缺失即 422 | 用户原始自然语言请求,如 `"来一首粤语老情歌，要有磁性的男声伴唱"` |
| `scheme` | 否 | `"B"` | 加工方案(仅 instrumental=true 时生效):`"B"` 包裹(零成本)/ `"C"` Gemini 预改写(需 key)。开关为 false 时**静默忽略** |
| `generate` | 否 | `false` | `true` 时附带一次真实 Lyria 生成(需 key,十几~几十秒,超时设 **≥120s**) |
| `fallback_b` | 否 | `true` | 仅 scheme=`"C"` 时生效:改写失败自动回落 B;`false` 则直接报 502 |

**最小可用请求(只传两个必填):**

```json
{ "user_input": "来一首粤语老情歌，要有磁性的男声伴唱", "instrumental": true }
```

### 出参

**前三个字段——每次响应都有:**

- **`prompt`** ★ **核心产物**。最终发给 Lyria 的 prompt,拿去塞进你们自己的生成请求
- **`scheme`** —— 实际使用的方案:`"B"` / `"C"` / `"B(fallback)"` / `"passthrough"`(= instrumental 为 false 的透传)
- **`ok`** —— 请求成功即 `true`

**后三个字段——只有 `generate=true` 才有值,平时是 `null`(字段本身永远在,判值即可,不用判存在):**

- **`audio`** —— 便捷音频提取:`{ "mime_type": "audio/mp3", "base64": "…" }`;版权静默拦截等空返回时为 `null`
- **`generation_text`** —— 通常为 `"[[A0]]"`;**出现其他文本 = 含人声**,可作线上监控
- **`lyria_response`** —— Lyria 原始响应全量(音频 base64),需要哪个字段取哪个

### 默认情况一句话总览(不传任何可选参数时会发生什么)

| 你传的 instrumental | 服务做什么 | 返回 scheme | 需 key | 耗时 |
|---|---|---|---|---|
| `true`(默认 scheme=B) | 用户输入包进系统提示词规则框 | `"B"` | ❌ | 毫秒级 |
| `false` | 用户输入原样透传,零加工 | `"passthrough"` | ❌ | 毫秒级 |

## 1. 快速开始

```bash
cd demo
pip install -r requirements.txt
python3 -m instrumental_prompt.run_server --port 8300
# (等价写法: uvicorn instrumental_prompt.main:app --host 0.0.0.0 --port 8300)
# 生产路径(instrumental=true+scheme B / 透传)不需要配任何 key
# 要用 scheme C 或 generate=true 时:cp .env.example .env 并填 key
```

启动后浏览器开 `http://<host>:8300/docs` 可交互试用——请求与响应的完整字段契约都在里面(响应结构由 response_model 声明,可直接当接口文档用)。

## 2. 调用方法(核心)

### 2.1 `POST /prompt` —— 唯一业务端点

```bash
curl -X POST http://localhost:8300/prompt \
    -H "Content-Type: application/json" \
    -d '{"user_input": "来一首粤语老情歌，要有磁性的男声伴唱", "instrumental": true}'
```

响应:

```json
{ "ok": true, "scheme": "B", "prompt": "你是一个专业的音乐生成助手。……" }
```

**后端集成只需两步**:① POST 拿 `prompt`;② 把它塞进你们自己的 Lyria 生成请求的 prompt 字段,走既有链路。(入参出参明细见顶部「⚡ 接口速查」)

**响应 `scheme` 值域:** `"B"` / `"C"` / `"B(fallback)"` / `"passthrough"`(instrumental=false)。

**响应形状**:六个字段永远都在——`generate=false` 时 `lyria_response`/`audio`/`generation_text` 为 `null`。取字段判值即可,不用判 key 存在性。

**generate=true 时后三个字段有值:**

```json
{
  "lyria_response": { "…Lyria 原始响应全量,音频 base64…" },
  "audio": { "mime_type": "audio/mp3", "base64": "SUQz…" },
  "generation_text": "[[A0]]"
}
```

`audio` 在版权静默拦截等空返回时为 `null`;`generation_text` 除 `[[A0]]` 段标外出现文本 = 含人声,可作线上监控。

### 2.2 `GET /health`

```json
{ "ok": true, "model": "lyria-3-pro-preview", "gemini_key_present": true, "key_source": "namespaced" }
```

不调外部服务。`key_source` 见 FAQ Q2。

### 2.3 错误码

| 场景 | HTTP | body.detail |
|---|---|---|
| `user_input` 缺失/空白、`instrumental` 漏传、`scheme` 非法 | 422 | FastAPI 校验错误 / 明确中文信息 |
| token 错(设了 API_TOKEN 才有) | 401 | `unauthorized` |
| scheme=C 失败且 fallback_b=false | 502 | `scheme_c_failed: …` |
| Lyria 异常(400 地域/503 负载/网络) | 502 | `lyria_error: …` |
| generate=true 但未配 key | 500 | `GEMINI_API_KEY 未配置` |

400(地域/VPN)重试即可;503(高负载)稍后重试;重试策略由调用方定。

## 3. 部署与安全 FAQ

**Q1:key 放哪?能写死在代码里吗?**

key 只放服务运行环境(env 或 `.env` 文件),**严禁写死在代码里**。原因:① key 进 git 历史即永久泄露(删掉也在历史里);② 交付拷贝/仓库同步时每份副本都带着 key。`.env` 已被 .gitignore 覆盖(本仓库验证过),不会进版本库。

**Q2:服务器上已经有别的 GEMINI_API_KEY(别的服务在用),会冲突吗?**

会,而且默认静默。python-dotenv 不覆盖已存在的环境变量——如果服务器环境里已导出 `GEMINI_API_KEY`,本服务会直接用那个 key(计费进对方项目、权限可能不符)。本服务的隔离做法:**优先读专用变量 `INSTRUMENTAL_PROMPT_GEMINI_API_KEY`**,只在没设专用变量时才回退 `GEMINI_API_KEY`。部署后 `GET /health` 看 `key_source`:`"namespaced"` = 在用专用 key(安全),`"generic"` = 在用机器通用 key(确认那真是你自己的),`"unset"` = 没配。

**Q3:不设鉴权会有什么风险?**

key 本身偷不走(不进 git、不回显于响应),但 `/prompt` 默认开放——陌生人能刷 scheme C / generate=true 烧你的 Gemini 配额。建议:内网部署,或在 `.env` 设 `API_TOKEN=xxx` 开启 Bearer 鉴权(设了之后 `/prompt` 必须带 `Authorization: Bearer xxx`)。

**Q4:`.env` 文件本身怎么防护?**

`chmod 600 .env`(仅运行用户可读)。未来容器化时 .env 不打进镜像。

**Q5:方案 B 和 C 怎么选?**

B(默认):零成本零延迟零依赖,不确定性在 Lyria 转写层行为(版本更新可能变,建议保留 generation_text 人声监控)。C:控制权在上游、人声词源头删除,成本是每次 +1 次 Gemini 调用,风险是改写波动/语义删减。两者实测均 100% 服从(35/35、41/41)。默认 B,C 失败自动回落 B(fallback_b=true)。

**Q6:生成的音乐时长/格式能控制吗?**

本服务不管生成参数——prompt 拿走后,生成请求的所有参数(模型、格式)由调用方自己的链路决定。`generate=true` 仅是试用/对照,模型默认 `lyria-3-pro-preview`。

## 4. 测试

```bash
cd demo && python3 -m pytest tests/ -v   # 需先 pip install pytest httpx
```

41 个用例覆盖 config/engine/providers/service/api 五层,不真调外部服务。

## 5. 行为依据

- 核心发现:Lyria prompt 通道前置通用语言模型,系统提示词类音乐需求可被理解执行(B 方案借此零成本约束)
- 实验归档:`../experiments/2026-08-no-vocals/`(37 条数据集、判定方法、逐用例对照)
- 交付报告:`../experiments/2026-08-no-vocals/deliverables/report.md`
