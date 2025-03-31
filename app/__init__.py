from fastapi import FastAPI
from .database import engine, Base
from . import models

# Создаем все таблицы при старте
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener Service",
    description="Сервис для сокращения длинных ссылок",
    version="0.1.0",
)

from .main import *