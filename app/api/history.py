import os
import aiofiles
import json
from typing import Any
from fastapi import HTTPException, APIRouter

from app.logger import logger

history_path = os.getenv("HISTORY_PATH")
state_path = os.getenv("STATE_PATH")

router = APIRouter()

async def get_history() -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())


@router.get("/history")
async def history() -> list[dict[str, Any]]:
    try:
        return await get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    
@router.get("/history/clear")
async def clear_history() -> None:
    try:
        async with aiofiles.open(history_path, "w") as file:
            await file.write(json.dumps([]))
        os.remove(state_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
