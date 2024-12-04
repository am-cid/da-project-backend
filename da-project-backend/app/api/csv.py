from typing import Annotated, Literal

from fastapi import APIRouter, File

from app.database import SessionDep
from app.models import CleanColumnData, RawCsv

router = APIRouter(prefix="/api/csv", tags=["CSV Handling"])


@router.post("/clean")
def preview_clean_csv(
    raw_csv: Annotated[RawCsv, File()],
    _: SessionDep,
    strategy: Literal[
        "forward", "backward", "min", "max", "mean", "zero", "one"
    ] = "zero",
) -> list[CleanColumnData]:
    return raw_csv.to_clean_columns(strategy)
