from contextlib import asynccontextmanager

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


app = FastAPI(
    title="Data Analytics Project API",
    description=(
        "This API provides endpoints for interacting with data reports, pages, columns, and comments. "
        "It allows users to create, update, delete, and fetch reports, as well as manage the pages and columns "
        "within those reports. The API also includes functionalities for interacting with comments on report pages, "
        "and performing data analysis operations on columns in reports. Additionally, the Gemini integration allows "
        "users to prompt a model for analysis and insights."
    ),
    summary=(
        "An API for managing reports, pages, columns, and comments in a data analytics project. "
        "It also provides data analysis operations and Gemini integration for model-based insights."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"], 
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],)

app.include_router(report)
app.include_router(page)
app.include_router(column)
app.include_router(comment)
app.include_router(gemini)
