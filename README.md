# Lyria 提示词处理服务

> 一个可独立部署的后端组件:**用户输入 + 模式选择(instrumental/lyrics/passthrough) → 最终 Lyria prompt**。
> 生产路径零 key 零依赖毫秒级返回;真实 Lyria 生成是可选的试用能力。
> 实验依据(100% 服从实测):`../experiments/2026-08-no-vocals/`(报告在 `deliverables/`)。

## ⚡ 接口速查(入参 / 出参 / 默认值)——最重要的一节

**`POST /prompt`**,请求体 JSON。

> ### ⚠️ `mode` 必填,没有默认值!
> **请求里不带 `mode` 字段 → 直接 422 拒绝,服务不会替你猜。**
> 三个值:`"passthrough"` 原样透传 / `"instrumental"` 纯音乐 / `"lyrics"` 歌词模式。
> (另一个必填是 `user_input`;其余四个字段都有默认,不传也行。)

### 入参(6 个字段)

| 字段 | 必填 | 不传时的默认 | 说明 |
|---|---|---|---|
| **`mode`** | **✅ 必填** | **无!漏传即 422** | `"passthrough"` 原样透传 / `"instrumental"` 纯音乐(B/C) / `"lyrics"` 歌词模式(S1/S2) |
| **`user_input`** | **✅ 必填** | 无,缺失即 422 | 主输入。passthrough/instrumental=完整自然语言描述;lyrics=**风格描述**(对应前端风格框,≤3000 字符) |
| `lyrics_input` | lyrics 模式必填非空白 | `""` | 歌词框原文。**仅 mode="lyrics" 允许非空**,≤1000 字符,超限 422(不截断——实测 5000 字会产生截断歌/空返回) |
| `scheme` | 否 | instrumental→`"B"` / lyrics→`"S2"` | 模式内子路由。instrumental 可填 `"B"` 包裹/`"C"` Gemini 改写;lyrics 可填 `"S2"` 冻结模板/`"S1"` 裸拼接对照;**passthrough 不要传**(传了 422) |
| `generate` | 否 | `false` | `true` 时附带一次真实 Lyria 生成(需 key,十几~几十秒,超时设 **≥120s**) |
| `fallback_b` | 否 | `true` | 仅 instrumental+scheme=C 生效:改写失败自动回落 B;`false` 则直接报 502 |

**最小可用请求:**

```json
{ "user_input": "来一首粤语老情歌，要有磁性的男声伴唱", "mode": "instrumental" }
```

**歌词模式请求:**

```json
{
  "user_input": "A happy Japanese Anime Song with bright female vocals",
  "mode": "lyrics",
  "lyrics_input": "早起的小猫 还在伸懒腰\n窗外的阳光 正在打信号"
}
```

### 出参

**前三个字段——每次响应都有:**

- **`prompt`** ★ **核心产物**。最终发给 Lyria 的 prompt,拿去塞进你们自己的生成请求
- **`scheme`** —— 实际使用的方案:`"B"` / `"C"` / `"B(fallback)"` / `"passthrough"` / `"S1"` / `"S2"`
- **`ok`** —— 请求成功即 `true`

**后三个字段——只有 `generate=true` 才有值,平时是 `null`(字段本身永远在,判值即可,不用判存在):**

- **`audio`** —— 便捷音频提取:`{ "mime_type": "audio/mp3", "base64": "…" }`;版权静默拦截等空返回时为 `null`
- **`generation_text`** —— 纯音乐成功通常为 `"[[A0]]"`;**歌词模式 = Lyria 实唱歌词**(`[[A0]]` 段标 + `[12.8:]` 时间戳行),建议落库审计"唱没唱对"
- **`lyria_response`** —— Lyria 原始响应全量(音频 base64),需要哪个字段取哪个

### 三模式默认行为一句话总览(不传任何可选参数)

| 你传的 mode | 服务做什么 | 返回 scheme | 需 key | 耗时 |
|---|---|---|---|---|
| `"instrumental"` | 用户输入包进纯音乐系统提示词 | `"B"` | ❌ | 毫秒级 |
| `"lyrics"` | 风格+歌词清洗后合并进 S2 冻结模板 | `"S2"` | ❌ | 毫秒级 |
| `"passthrough"` | 用户输入原样透传,零加工 | `"passthrough"` | ❌ | 毫秒级 |

### 歌词模式输入清洗(自动执行,调用方无感)

两槽(user_input/lyrics_input)自动做:① `</user_input>`、`<style>` 等标签串剥除;② 高危句式(**忽略以上/系统指令/指令更新/不要人声/纯音乐/重新生成/改为生成**)命中 → **422 整单拒绝**(`detail: injection_rejected: <字段名>`)。常规歌词实测零误伤;注入是 Lyria 模型层固有弱点,只能输入侧拦(实测依据见 lyrics-merge 实验)。

## 1. 快速开始

```bash
cd demo
pip install -r requirements.txt
python3 -m instrumental_prompt.run_server --port 8300
# (等价写法: uvicorn instrumental_prompt.main:app --host 0.0.0.0 --port 8300)
# 生产路径(instrumental+scheme B / lyrics+scheme S2 / passthrough)不需要配任何 key
# 要用 scheme C 或 generate=true 时:cp .env.example .env 并填 key
```

启动后浏览器开 `http://<host>:8300/docs` 可交互试用——请求与响应的完整字段契约都在里面(响应结构由 response_model 声明,可直接当接口文档用)。

## 2. 调用方法(核心)

### 2.1 `POST /prompt` —— 唯一业务端点

```bash
curl -X POST http://localhost:8300/prompt \
    -H "Content-Type: application/json" \
    -d '{"user_input": "来一首粤语老情歌，要有磁性的男声伴唱", "mode": "instrumental"}'
```

响应:

```json
{ "ok": true, "scheme": "B", "prompt": "你是一个专业的音乐生成助手。……" }
```

**后端集成只需两步**:① POST 拿 `prompt`;② 把它塞进你们自己的 Lyria 生成请求的 prompt 字段,走既有链路。(入参出参明细见顶部「⚡ 接口速查」)

**响应 `scheme` 值域:** `"B"` / `"C"` / `"B(fallback)"` / `"passthrough"` / `"S1"` / `"S2"`。

**响应形状**:六个字段永远都在——`generate=false` 时 `lyria_response`/`audio`/`generation_text` 为 `null`。取字段判值即可,不用判 key 存在性。

**generate=true 时后三个字段有值:**

```json
{
  "lyria_response": { "…Lyria 原始响应全量,音频 base64…" },
  "audio": { "mime_type": "audio/mp3", "base64": "SUQz…" },
  "generation_text": "[[A0]]"
}
```

`audio` 在版权静默拦截等空返回时为 `null`;`generation_text` 在纯音乐成功时为 `[[A0]]`,歌词模式包含实际演唱歌词(段标+时间戳)。

### 2.2 `GET /health`

```json
{ "ok": true, "model": "lyria-3-pro-preview", "gemini_key_present": true, "key_source": "namespaced" }
```

不调外部服务。`key_source` 见 FAQ Q2。

### 2.3 错误码

| 场景 | HTTP | body.detail |
|---|---|---|
| mode/scheme 非法、组合矛盾、长度超限、必填字段缺失 | 422 | FastAPI 校验错误 / 明确中文信息 |
| 歌词输入命中高危句式 | 422 | `injection_rejected: lyrics_input` |
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

**Q5:纯音乐方案 B 和 C 怎么选?**

B(默认):零成本零延迟零依赖,不确定性在 Lyria 转写层行为(版本更新可能变,建议保留 generation_text 监控)。C:控制权在上游、人声词源头删除,成本是每次 +1 次 Gemini 调用,风险是改写波动/语义删减。两者实测均 100% 服从(35/35、41/41)。默认 B,C 失败自动回落 B(fallback_b=true)。

**Q6:生成的音乐时长/格式能控制吗?**

本服务不管生成参数——prompt 拿走后,生成请求的所有参数(模型、格式)由调用方自己的链路决定。`generate=true` 仅是试用/对照,模型默认 `lyria-3-pro-preview`。

## 4. 测试

```bash
cd demo && python3 -m pytest tests/ -v   # 需先 pip install pytest httpx
```

74 个用例覆盖 config/engine/providers/service/api 五层,不真调外部服务。

## 5. 行为依据

- 核心发现:Lyria prompt 通道前置通用语言模型,系统提示词类音乐需求可被理解执行(B 方案借此零成本约束)
- 实验归档:`../experiments/2026-08-no-vocals/`(37 条数据集、判定方法、逐用例对照)
- 交付报告:`../experiments/2026-08-no-vocals/deliverables/report.md`
