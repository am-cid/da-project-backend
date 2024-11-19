from contextlib import asynccontextmanager

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI

from app.database import create_db_and_tables

from .column import router as column
from .comment import router as comment
from .gemini import router as gemini
from .page import router as page
from .report import router as report


@asynccontextmanager
async def lifespan(_: FastAPI):
    # startup
    create_db_and_tables()
    load_dotenv()
    genai.configure()
    # end startup
    yield
    # shutdown
    # end shutdown


app = FastAPI(lifespan=lifespan)
app.include_router(report)
app.include_router(page)
app.include_router(column)
app.include_router(comment)
app.include_router(gemini)
