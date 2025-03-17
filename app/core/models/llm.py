import os
import yaml
import aiofiles
from typing import Any
from openai import AsyncAzureOpenAI

model_config_path = os.getenv("MODEL_CONFIG_PATH")

class LLM:
    def __init__(self, model: str):
        self.model = model
        self.response_format = response_format
        self.model_client = None
    
    @classmethod
    async def create(cls, model: str) -> "LLM":
        instance = cls(model)
        instance.model_client = await instance.get_model_client()
        return instance.model_client

    async def get_model_client(self):
        try:
            async with aiofiles.open(model_config_path, "r") as file: 
                configs = yaml.safe_load(await file.read())
                model_config = configs['models'][self.model]

            self.azure_deployment = model_config['config']['azure_deployment']
                
            return AsyncAzureOpenAI(
                api_key=model_config['config']['api_key'],
                azure_endpoint=model_config['config']['azure_endpoint'],
                api_version=model_config['config']['api_version']
            )
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise RuntimeError(f"Failed to load model config: {e}")

    async def get_completion(self, prompt:str, response_format: Any, temperature: float = 0, max_tokens: int = 1000) -> str:
        if not self.model_client:
            raise RuntimeError("Model client not initialized")

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]

            completion = await self.model_client.chat.completions.create(
                model=self.azure_deployment,
                messages=messages,
                response_format=response_format if response_format else {"type": "text"},
                temperature=temperature,
                max_tokens=max_tokens
            )

            return completion.choices[0].message.content

        except Exception as e:
            raise Exception(f"Error generating completion: {str(e)}")
                
