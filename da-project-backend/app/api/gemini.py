from typing import Literal

import google.generativeai as genai
from fastapi import APIRouter

from app.database import SessionDep

router = APIRouter(prefix="/api/gemini", tags=["gemini"])


@router.post("/")
def prompt_gemini(
    _: SessionDep,
    *,
    prompt: str,
    context: dict[str, str] = {},
    model: Literal[
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ] = "gemini-1.5-flash",
) -> str:
    prompt = f"""
<system>
Since this request comes from an API, I expect to only get the answer without
acknowledgement from you. Do not use unsure tone and terms such as "likely",
"probably", etc. Keep it professional. Do not hallucinate.
</system>
<prompt>
{prompt}
</prompt>"""
    for tag, content in context.items():
        prompt += f"""
<{tag}>
{content}
</{tag}>
"""
    res = genai.GenerativeModel(model).generate_content(prompt)
    return res.text
