import os
import aiofiles
import yaml
from dotenv import load_dotenv
from typing import Any, List, Literal
from pydantic import BaseModel
from enum import Enum

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from app.core.agents.prompts import intent_prompt

model_config_path = os.getenv("MODEL_CONFIG_PATH")

class IntentType(str, Enum):
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation" 
    TEXT_GENERATION = "text_generation"

class IntentOutput(BaseModel):
    intent: Literal["question_answering", "summarization", "translation", "text_generation"]
    model: Literal["chat", "reasoning"]
            
class IntentAgent:
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.system_message = intent_prompt
        self.model_client = None
        self.agent = None

    @classmethod
    async def create(cls, name: str, model: str) -> "IntentAgent":  # Fix return type
        instance = cls(name, model)
        instance.model_client = await instance.get_model_client()
        instance.agent = instance.initialize_agent()
        return instance.agent

    async def get_model_client(self):
        try:
            async with aiofiles.open(model_config_path, "r") as file:  # Add error handling
                configs = yaml.safe_load(await file.read())
                model_config = configs['models'][self.model]
                model_config['config']['response_format'] = IntentOutput

                print(IntentOutput.model_json_schema())
                print(model_config)
                print('here???')
            # return ChatCompletionClient.load_component(model_config)
            return AzureOpenAIChatCompletionClient(
                model=model_config['config']['model'],
                api_key=model_config['config']['api_key'],
                azure_endpoint=model_config['config']['azure_endpoint'],
                azure_deployment=model_config['config']['azure_deployment'],
                api_version=model_config['config']['api_version'],
                response_format=IntentOutput
            )
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise RuntimeError(f"Failed to load model config: {e}")

    def initialize_agent(self):
        if not self.model_client:
            raise RuntimeError("Model client not initialized")
        return AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self.system_message,
        )