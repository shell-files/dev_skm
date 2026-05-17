from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.settings import settings
from src.utils.fastset import run

app = run()


@app.get("/")
def read_root():
  return {"msg": "SKM!"}

