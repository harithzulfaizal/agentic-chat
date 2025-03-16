import json
import logging
import os
from typing import Any, Awaitable, Callable, Optional, Sequence
import json_repair
from datetime import datetime

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent, AgentEvent, ChatMessage, ToolCallExecutionEvent, ToolCallRequestEvent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.logger import logger
from app.api.history import get_history
from app.core.agents.intent_agent import IntentAgent
from app.core.agents.assistant_agent import KijangAgent
from app.core.agents.prompts import kijang_prompt

model_config_path = os.getenv("MODEL_CONFIG_PATH")

router = APIRouter()

history_path = os.getenv("HISTORY_PATH")
state_path = os.getenv("STATE_PATH")

async def get_team(
    user_input_func: Callable[[str, Optional[CancellationToken]], Awaitable[str]],
) -> RoundRobinGroupChat:
    # Get model client from config.
    async with aiofiles.open(model_config_path, "r") as file:
        configs = yaml.safe_load(await file.read())
        model_config = configs["models"]["gpt-4o-mini"]
    model_client = ChatCompletionClient.load_component(model_config)

    intent_agent = await IntentAgent.create(
        name="IntentAgent",
        model="gpt-4o-mini",
    )

    kijang_agent = await KijangAgent.create(
        name="AssistantAgent",
        model="gpt-4o-mini",
        system_message=kijang_prompt.format(current_datetime=datetime.now().strftime('%Y-%m-%d'))
    )

    kijang_reasoning_agent = await KijangAgent.create(
        name="ReasoningAgent",
        model="o3-mini",
        system_message="You are a helpful assistant. You excel in complex reasoning tasks.",
    )

    user_proxy = UserProxyAgent(
        name="user",
        input_func=user_input_func,  # Use the user input function.
    )

    def selector_func_with_user_proxy(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        if messages[-1].source == user_proxy.name:
            return intent_agent.name
        if messages[-1].source == intent_agent.name:
            agent_router = json_repair.loads(messages[-1].content)

            if agent_router["model"] == "chat":
                return kijang_agent.name
            elif agent_router["model"] == "reasoning":
                return kijang_reasoning_agent.name
        if messages[-1].source in [kijang_agent.name, kijang_reasoning_agent.name]:
            return user_proxy.name
        return None
    
    team = SelectorGroupChat(
        [intent_agent, kijang_agent, kijang_reasoning_agent, user_proxy],
        model_client=model_client,
        selector_func=selector_func_with_user_proxy
    )
    # Load state from file.
    if not os.path.exists(state_path):
        return team
    async with aiofiles.open(state_path, "r") as file:
        state = json.loads(await file.read())
    await team.load_state(state)
    return team

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
                            source="AssistantAgent",
                            content="Conducting web search..."
                        )
                    if isinstance(message, ToolCallExecutionEvent):
                        print(message)
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