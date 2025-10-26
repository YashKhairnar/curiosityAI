from flask import current_app, g
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
import os
from app.utils.embeddingModels import MyEmbeddingFunction

def get_chroma_client() -> ClientAPI:
    if 'chroma_client' not in g:
        g.chroma_client = chromadb.CloudClient(
            api_key=os.environ.get("CHROMA_API_KEY"),
            tenant=os.environ.get("CHROMA_TENANT"),
            database=os.environ.get("CHROMA_DATABASE")
        )
    return g.chroma_client
    
def get_chroma_collection() -> Collection:
    chroma_client = get_chroma_client()
    if 'chroma_collection' not in g:
        g.chroma_collection = chroma_client.get_or_create_collection(
            name="my_collection",
            embedding_function=MyEmbeddingFunction()
        )

    return g.chroma_collection