import os
import aiofiles
import yaml
from dotenv import load_dotenv
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

from app.core.tools.web_search import get_relevant_web_pages

model_config_path = os.getenv("MODEL_CONFIG_PATH")
            
class KijangAgent:
    def __init__(self, name: str, model: str, system_message: str):
        self.name = name
        self.model = model
        self.system_message = system_message
        self.model_client = None
        self.agent = None

    @classmethod
    async def create(cls, name: str, model: str, system_message: str) -> "KijangAgent":  # Fix return type
        instance = cls(name, model, system_message)
        instance.model_client = await instance.get_model_client()
        instance.agent = instance.initialize_agent()
        return instance.agent

    async def get_model_client(self):
        try:
            async with aiofiles.open(model_config_path, "r") as file:  # Add error handling
                configs = yaml.safe_load(await file.read())
                model_config = configs['models'][self.model]
                print("init model config", model_config)
            return ChatCompletionClient.load_component(model_config)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise RuntimeError(f"Failed to load model config: {e}")

    def initialize_agent(self):
        if not self.model_client:
            raise RuntimeError("Model client not initialized")
        return AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self.system_message,
            tools=[get_relevant_web_pages],
            reflect_on_tool_use=True,
            tool_call_summary_format=True
        )