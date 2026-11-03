# 知衡前端

企业制度与流程核验台。保留原有文档入库、知识问答和 SSE 接口，仅替换前端产品语义与交互展示。零构建、零 CDN，纯 HTML / CSS / JavaScript。

![知衡预览](./preview-enterprise.png)

## 本地预览

```bash
python frontend/mock_server.py
```

打开 <http://127.0.0.1:8765>。

`mock_server.py` 同时提供静态文件和假数据接口，用来验证交互、SSE 流式解析和上传进度。没有启动后端时，直接双击 `index.html` 也会自动进入演示模式（会预置 4 份企业示例资料）。

为保持后端业务流程不变，`mock_server.py` 仍返回原有接口演示数据。查看企业化前端演示时，可在地址后追加 `?demo=1`；该模式使用前端内置的制度、审批流程、合同审核和信息安全 SOP 示例。

## 文件

```text
frontend/
  index.html       页面结构
  styles.css       视觉样式与响应式布局
  app.js           上传、核验问答、SSE 解析、Markdown 渲染、企业演示数据
  mock_server.py   本地联调用 mock 服务（仅标准库）
```

## 后端接口契约

### `GET /api/v1/health`

```json
{ "status": "ok" }
```

前端据此切换「已连接」和「演示模式」。

### `POST /api/v1/documents`

`multipart/form-data`，字段名 `file`。

```json
{ "doc_id": "doc-1", "file_name": "lecture.pdf", "pages": 24, "chunks": 71 }
```

上传过程中前端用 XHR 的 `upload.onprogress` 显示进度。

### `POST /api/v1/chat`

请求：

```json
{ "session_id": "uuid", "question": "客户申请非标折扣时如何审批？", "top_k": 4 }
```

响应：`text/event-stream`，每个事件以空行结尾。

| event | data | 说明 |
|---|---|---|
| `meta` | `{"session_id": "..."}` | 会话 ID，可覆盖前端生成的临时 ID |
| `status` | `{"message": "..."}` | 当前处理阶段提示 |
| `sources` | `{"sources": [...]}` | 检索结果，建议在 token 之前发送 |
| `token` | `{"text": "增量文本"}` | 流式生成片段 |
| `replace` | `{"text": "完整文本"}` | 用校验或修复后的完整回答替换当前内容 |
| `refusal` | `{"reason": "..."}` | 检索不足，前端展示拒答卡片 |
| `done` | `{"latency_ms": 1234}` | 本轮结束 |
| `error` | `{"message": "..."}` | 统一错误出口 |

`sources` 中每一项：

```json
{
  "index": 1,
  "file_name": "大客户报价与折扣审批流程.md",
  "page": 4,
  "snippet": "低于标准折扣下限的报价，须经财务测算并由事业部总经理审批。"
}
```

`index` 必须和回答里的 `[1]` 对应。前端只把存在于 `sources` 里的编号渲染成可点击引用。

Python 端一个最小的 SSE 写法：

```python
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@app.post("/api/v1/chat")
async def chat(body: ChatRequest):
    async def generate():
        yield sse("meta", {"session_id": body.session_id})
        yield sse("sources", {"sources": sources})
        async for token in stream_answer(body.question):
            yield sse("token", {"text": token})
        yield sse("done", {"latency_ms": elapsed})

    return StreamingResponse(generate(), media_type="text/event-stream")
```

## 挂到 FastAPI

先注册所有 `/api` 路由，再挂静态目录（顺序不能反）：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

开发阶段建议前端单独跑 `mock_server.py`，在 `app.js` 里把 `API_BASE` 指向 `http://127.0.0.1:8000/api/v1` 即可；生产环境同源部署时无需修改。

## 已处理的边界

- 流式解析兼容 `\n` 与 `\r\n`，忽略心跳注释行，处理跨 chunk 的半截事件。
- Markdown 先转义再渲染，引用编号只认本轮 `sources`，避免 XSS 和模型伪造引用。
- 引用点击会展开来源卡片并高亮对应片段。
- 上传限制 20MB，只接受 PDF / MD / TXT；失败会从列表回滚。
- 断线、HTTP 错误、后端 `error` 事件都会落到同一条错误展示路径。
- 侧栏在窄屏变为抽屉，支持 Esc 关闭；`prefers-reduced-motion` 下关闭动画。
