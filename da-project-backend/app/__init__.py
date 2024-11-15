from .api import app
from .database import create_db_and_tables


# TODO: https://fastapi.tiangolo.com/advanced/events/
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
