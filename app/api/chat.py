import json
import logging
import os
from typing import Any, Awaitable, Callable, Optional, Sequence, List
import json_repair
from datetime import datetime

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent, FunctionExecutionResult,ToolCallExecutionEvent, ToolCallRequestEvent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.logger import logger
from app.api.history import get_history
from app.core.agents.orchestrator import get_team
from app.core.tools.web_search import WebPage

model_config_path = os.getenv("MODEL_CONFIG_PATH")

router = APIRouter()

history_path = os.getenv("HISTORY_PATH")
state_path = os.getenv("STATE_PATH")

@router.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()

    # User input function used by the team.
    async def _user_input(prompt: str, cancellation_token: CancellationToken | None) -> str:
        data = await websocket.receive_json()
        message = TextMessage.model_validate(data)
        return message.content

    try:
        while True:
            # Get user message.
            data = await websocket.receive_json()
            request = TextMessage.model_validate(data)
            print(request)

            try:
                print("Getting team")
                # Get the team and respond to the message.
                team = await get_team(_user_input)
                history = await get_history()
                stream = team.run_stream(task=request)
                async for message in stream:
                    if isinstance(message, TaskResult):
                        continue
                    if isinstance(message, ToolCallRequestEvent):
                        message = TextMessage(
                            source="WebSearchTool",
                            content="Conducting web search..."
                        )
                    if isinstance(message, ToolCallExecutionEvent):
                        print("tool output -------- ", message)
                        
                        function_results = message.content
                        for result in function_results:
                            if isinstance(result, FunctionExecutionResult) and not result.is_error and result.name == "get_relevant_web_pages":
                                webpages = eval(result.content)  # This assumes result.content is a string representation of a list
                                for webpage in webpages:
                                    print("inside web page -----", webpage.url)
                                    await websocket.send_json({
                                        "source": webpage.url,
                                        "content": webpage.content,
                                        "type": "WebPageContent"
                                    })
                        continue
                    print(message)
                    await websocket.send_json(message.model_dump())
                    if not isinstance(message, UserInputRequestedEvent):
                        # Don't save user input events to history.
                        history.append(message.model_dump())
                        print(message.model_dump())

                    # Save team state to file.
                    print("before Saving state")
                    async with aiofiles.open(state_path, "w") as file:
                        print("saving state")
                        state = await team.save_state()
                        await file.write(json.dumps(state))

                    # Save chat history to file.
                    print("before Saving history")
                    async with aiofiles.open(history_path, "w") as file:
                        print("saving history")
                        await file.write(json.dumps(history))
                    
            except Exception as e:
                # Send error message to client
                error_message = {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "source": "system"
                }
                await websocket.send_json(error_message)
                # Re-enable input after error
                await websocket.send_json({
                    "type": "UserInputRequestedEvent",
                    "content": "An error occurred. Please try again.",
                    "source": "system"
                })
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Unexpected error: {str(e)}",
                "source": "system"
            })
        except:
            pass