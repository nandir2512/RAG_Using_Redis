# ---- Import statements ---- 
import os
from redisvl.index import AsyncSearchIndex
from redisvl.utils.vectorize import HFTextVectorizer
from redisvl.extensions.cache.embeddings import EmbeddingsCache
from redisvl.query import VectorQuery
import openai
import getpass

# ---- Environment setup ----
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

os.environ["REDIS_URL"] = REDIS_URL
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---- OpenAI API setup ----
CHAT_MODEL = "gpt-4.1"

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass("OPENAI_API_KEY :")

BASE_URL = os.environ["OPENAI_API_BASE"]


# ---- System prompt for the LLM ----
SYSTEM_PROMPT = """You are a helpful financial analyst assistant that has access
to public financial 10k documents in order to answer user's questions about company
performance, ethics, characteristics, and core information."""


# ---- Vectorizer and index setup from Lab 2 ----
hf = HFTextVectorizer(
    model="sentence-transformers/all-MiniLM-L6-v2",
    cache=EmbeddingsCache(
        name="embedcache",
        ttl=600,
        redis_url=REDIS_URL,
    )
)

index_name = "redisvl"

schema = {
  "index": {
    "name": index_name,
    "prefix": "chunk"
  },
  "fields": [
    {
        "name": "chunk_id",
        "type": "tag",
        "attrs": {
            "sortable": True
        }
    },
    {
        "name": "content",
        "type": "text"
    },
    {
        "name": "text_embedding",
        "type": "vector",
        "attrs": {
            "dims": 384,
            "distance_metric": "cosine",
            "algorithm": "hnsw",
            "datatype": "float32"
        }
    }
  ]
}

async_index = AsyncSearchIndex.from_dict(schema, redis_url=REDIS_URL)


# ---- Function to embed a query from Lab 2 (both standalone and class method versions) ----
def embed_query(query: str):
    """Convert a user query into a dense vector representation."""
    return hf.embed(query)

def embed_query_class(self, query: str):
    """Convert a user query into a dense vector representation."""
    return self.vectorizer.embed(query)


# ---- Function to retrieve context from Redis using vector search from Lab 2 (both standalone and class method versions) ---- 
async def retrieve_context(index, query_vector):
    """Standalone context retriever."""
    results = await index.query(
        VectorQuery(
            vector=query_vector,
            vector_field_name="text_embedding",
            return_fields=["content"],
            num_results=3
        )
    )
    return "\n".join([r["content"] for r in results])

async def retrieve_context_class(self, query_vector) -> str:
    """Fetch the relevant context from Redis using vector search"""
    results = await self.index.query(
        VectorQuery(
            vector=query_vector,
            vector_field_name="text_embedding",
            return_fields=["content"],
            num_results=3
        )
    )
    return "\n".join([result["content"] for result in results])


# ---- Function to format the query for the LLM from Lab 2----
def promptify(query: str, context: str) -> str:
    return f'''Use the provided context below derived from public financial
    documents to answer the user's question. If you can't answer the user's
    question, based on the context; do not guess. If there is no context at all,
    respond with "I don't have enough context to answer this question.".

    User question:

    {query}

    Helpful context:

    {context}

    Answer:
    '''

# ---- Function to generate the LLM response from Lab 2 ----
async def generate_llm_response(query: str, context: str, session: list = None) -> str:
    """Construct and send a complete prompt to the OpenAI LLM and return its response."""

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}] +
        (session or []) +
        [{"role": "user", "content": promptify(query, context)}]
    )

    response = await openai.AsyncClient(base_url=BASE_URL).chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.1,
        seed=42
    )

    return response.choices[0].message.content


# ---- Function to answer a question using the RAG pipeline from Lab 2 ----
async def answer_question(index: AsyncSearchIndex, query: str):
    """End-to-end RAG: embeds query, retrieves context, generates LLM response"""

    # Step 1: Embed the query
    query_vector = embed_query(query)

    # Step 2: Retrieve matching context chunks from Redis
    context = await retrieve_context(index, query_vector)

    # Step 3: Generate response from OpenAI using system prompt + context
    return await generate_llm_response(query, context)