from typing import Annotated

from fastapi import APIRouter, File

from app.database import SessionDep
from app.models import CleanColumnData, RawCsv

router = APIRouter(prefix="/api/csv", tags=["CSV Handling"])


@router.post("/clean")
def preview_clean_csv(
    raw_csv: Annotated[RawCsv, File()],
    _: SessionDep,
) -> list[CleanColumnData]:
    return raw_csv.to_clean_columns()
