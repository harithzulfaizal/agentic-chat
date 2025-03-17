import os
import yaml
import aiofiles
from typing import Any
from openai import AsyncAzureOpenAI

model_config_path = os.getenv("MODEL_CONFIG_PATH")

class Embedding:
    def __init__(self, model: str):
        self.model = model
        self.model_client = None
    
    @classmethod
    async def create(cls, model: str) -> "Embedding":
        instance = cls(model)
        instance.model_client = await instance.get_model_client()
        return instance

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

    async def get_embedding(self, query: str) -> str:
        if not self.model_client:
            raise RuntimeError("Model client not initialized")

        try:
            response = await self.model_client.embeddings.create(
                input=[query],
                model=self.azure_deployment
            )

            return response.data[0].embedding

        except Exception as e:
            raise Exception(f"Error generating embedding: {str(e)}")
                
