import os
from datetime import datetime
from typing import Optional, Tuple, Literal, List, Dict
from pydantic import Field, BaseModel
import numpy as np
import json
import json_repair
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

from app.core.agents.prompts import query_extraction_prompt
from app.core.models.llm import LLM
from app.core.models.embedding import Embedding

class QueryExtractionOutput(BaseModel):
    query: str = Field(
        ...,
        title="Original query",
        description="The original query string provided by the user"
    )
    route: int = Field(
        ...,
        title="System route",
        description=(
            "Choose between system 1 for questions related to the Bank's management, "
            "committees, board, stakeholders, organization structure, officers, and departments.\n"
            "Use 2 for questions related to the Bank's publicly available data example policy "
            "documents, reports, reviews, drafts, releases, speeches, statements, publications, "
            "financial concepts, definitions of financial concepts.\n"
            "If the query is too vague and you are unsure to choose the system, always default to 2.\n"
            "For any financial concepts, products such as credit cards, policy requirements such as "
            "employee screening opt for system 2.\n"
            "When in doubt, opt for system 2."
        ),
        ge=1,
        le=2
    )
    summarize: bool = Field(
        ...,
        title="Summarization needed",
        description="Whether the query requests a document summary"
    )
    temporal: bool = Field(
        ...,
        title="Temporal aspect",
        description="If query involves any temporal aspect (past, present, future, date)"
    )
    datetime_mentioned: bool = Field(
        ...,
        title="DateTime mentioned",
        description="If specific datetime is explicitly mentioned"
    )
    yearly: bool = Field(
        ...,
        title="Year-level information",
        description="If only year is mentioned or quarterly information needed"
    )
    monthly: bool = Field(
        ...,
        title="Month-level information", 
        description="If only month or explicit date with day/month mentioned"
    )
    recently: bool = Field(
        ...,
        title="Recent information",
        description="If query implies recent/latest/newest information"
    )
    datetime: List[str] = Field(
        ...,
        title="DateTime strings",
        description="List of datetime strings in ISO format (%Y-%m-%dT%H:%M:%S.%fZ)"
    )

# llm = await LLM.create(model="gpt-4o-mini")

search_client = SearchClient(
      endpoint=f"https://{os.getenv('AISEARCH_CLIENT')}.search.windows.net/", 
      credential=AzureKeyCredential(os.getenv("AISEARCH_KEY")),
      index_name=os.getenv("AISEARCH_INDEX")
)

class Document(BaseModel):
    page_content: str
    metadata: dict = Field(default_factory=dict)
    type: Literal["Document"] = "Document"

# async def extract_query(query: str) -> str:
#     response = await llm.get_completion(
#         prompt=query_extraction_prompt.format(date=datetime.now().strftime('%Y-%m-%d'), query=query),
#         response_format=QueryExtractionOutput,
#     )
#     return json_repair.loads(response)

async def get_relevant_policy_documents(query: str, k: int = 10) -> List[Document]:
    results = await asemantic_hybrid_search_with_score(client=search_client, query=query, fields="content_vector", k=10)

    return results

async def asemantic_hybrid_search_with_score(
        client, query: str, fields: str, k: int = 4, filters: Optional[str] = None
    ) -> List[Tuple[Document, float]]:

    embed_client = await Embedding.create(model="text-embedding-ada-002")

    from azure.search.documents.models import VectorizedQuery

    results = await client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(
                vector=np.array(
                    await embed_client.get_embedding(query), dtype=np.float32
                ).tolist(),
                k_nearest_neighbors=50,
                fields=fields,
            )
        ],
        filter=filters,
        query_type="semantic",
        semantic_configuration_name="default",
        query_caption="extractive",
        query_answer="extractive",
        top=k,
    )

    semantic_answers = await results.get_answers() or []
    semantic_answers_dict: Dict = {}
    for semantic_answer in semantic_answers:
        semantic_answers_dict[semantic_answer.key] = {
            "text": semantic_answer.text,
            "highlights": semantic_answer.highlights,
        }

    docs = [
            (
                Document(
                    page_content=result.pop("content"),
                    metadata={
                        **(
                            json.loads(result["metadata"])
                            if "metadata" in result
                            else {
                                k: v
                                for k, v in result.items()
                                if k != "content_vector"
                            }
                        ),
                        **{
                            "captions": {
                                "text": result.get("@search.captions", [{}])[0].text,
                                "highlights": result.get("@search.captions", [{}])[
                                    0
                                ].highlights,
                            }
                            if result.get("@search.captions")
                            else {},
                            "answers": semantic_answers_dict.get(
                                json.loads(result["metadata"]).get("key"), ""
                            ),
                        },
                    },
                ),
                float(result["@search.score"]),
            )
            async for result in results
        ]
    return docs