import os
import pinecone
from genkit.retrievers import pinecone as pinecone_retriever
from . import config

class VectorDBService:
    def __init__(self, api_key: str, index_name: str):
        if not api_key:
            raise ValueError("Pinecone API key is required.")
        pinecone.init(api_key=api_key)
        self.retriever = pinecone_retriever.PineconeRetriever(index_name=index_name)

    def index(self, documents: list[dict]):
        """
        Indexes documents in Pinecone.
        Each document should be a dict, e.g., {"content": "...", "metadata": {"id": "..."}}
        """
        self.retriever.index(documents)
        print(f"Successfully indexed {len(documents)} documents.")

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """
        Retrieves relevant documents from Pinecone.
        Returns a list of document dictionaries.
        """
        retrieved_docs = self.retriever.retrieve(query, k=k)
        return [{"text": doc.text, "metadata": doc.metadata} for doc in retrieved_docs]

# A single, shared instance of the service
# This uses the configuration from the config.py file
# and assumes PINECONE_API_KEY is set as an environment variable.
vector_db_service = VectorDBService(
    api_key=os.getenv("PINECONE_API_KEY"),
    index_name=config.PINECONE_INDEX_NAME
)
