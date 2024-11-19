from contextlib import asynccontextmanager

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI

from app.database import create_db_and_tables

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
