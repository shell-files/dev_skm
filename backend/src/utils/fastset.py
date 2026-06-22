"""
fastset.py
레이어: Utils
역할: FastAPI 앱 초기화 — CORS 미들웨어 설정 및 라우터 등록.
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from src.utils.settings import settings
from src import apis
import importlib
import pkgutil
# from contextlib import asynccontextmanager
# from src.utils.kafkasv import startConsumer
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.staticfiles import StaticFiles

# # [STARTUP] 앱이 켜질 때 Kafka 실행
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     startConsumer()
#     print("🚀 Kafka Email Consumer Started...")
#     yield

def run():
    """FastAPI 앱을 구성하고 apis/ 폴더의 라우터를 자동 등록한 후 uvicorn으로 실행한다."""
    app = FastAPI(servers=[
        {"url": "/", "description": "API 기본 서버"}
    ])
    # 라우터 등록
    for _, module_name, _ in pkgutil.iter_modules(apis.__path__):
        module = importlib.import_module(f"src.apis.{module_name}")
        if hasattr(module, "router"):
            includeOptions = {"prefix": f"/{module_name}"}
            if module_name != "api":
                includeOptions["tags"] = [module_name]
            app.include_router(module.router, **includeOptions)

    # CORS 설정
    origins = ["http://localhost", settings.host_ip,
                f"http://skm.{settings.domain}",
                f"http://skm.{settings.skm_domain}",
                f"http://capybara.{settings.domain}",
                f"http://capybara.{settings.skm_domain}",
                # f"http://hg.{settings.domain}", f"http://tv.{settings.domain}"
                ]
    app.add_middleware(
				CORSMiddleware,
				allow_origins=origins,
				allow_credentials=True,
				allow_methods=["*"],
				allow_headers=["*"],
    )

    # Static Files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    Instrumentator().instrument(app).expose(app)
    return app

