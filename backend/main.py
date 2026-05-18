# 智途校园 — 大学生 AI 成长服务平台 - FastAPI 应用入口
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import traceback

from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.points import router as points_router
from app.api.plans import router as plans_router
from app.api.resumes import router as resumes_router
from app.api.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动和关闭"""
    print("[zhitu] 智途校园服务启动中...")
    print("[zhitu] Ready: http://localhost:8000")
    yield
    print("[zhitu] 智途校园服务已停止。")


app = FastAPI(
    title="智途校园 API",
    description="大学生 AI 成长服务平台 | 扣子Coze智能体驱动",
    version="2.0.0",
    lifespan=lifespan,
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由（必须在静态文件之前）
app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(points_router, prefix="/api")
app.include_router(plans_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"success": True, "message": "智途校园服务运行中"}


# 静态文件（CSS/JS/图片等）
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# SPA 回退：所有未匹配的 GET 请求返回 index.html
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """SPA 回退路由 — 非 API、非静态文件的请求返回 index.html"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse(status_code=404, content={"detail": "Not found"})
