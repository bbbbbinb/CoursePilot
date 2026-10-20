from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import PROJECT_ROOT

app = FastAPI(
    title="CoursePilot API",
    description="课程知识库 Agent 助教后端",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 必须先注册 API 路由；最后挂载在 "/" 的静态目录不能提前拦截 API 请求。
app.include_router(api_router)


@app.api_route(
    "/api/{unmatched_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def unmatched_api(unmatched_path: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": f"API endpoint not found: {unmatched_path}"},
    )


app.mount(
    "/",
    StaticFiles(directory=PROJECT_ROOT / "frontend", html=True),
    name="frontend",
)
