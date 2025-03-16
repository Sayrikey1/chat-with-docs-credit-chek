from typing import Any
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings, VectorStoreIndex
from llama_index.llms.groq import Groq
from llama_index.readers.web import SimpleWebPageReader

from langchain_community.embeddings import HuggingFaceEmbeddings

import torch
import os

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load documents using SimpleWebPageReader
    reader = SimpleWebPageReader(html_to_text=True)
    docs = reader.load_data('path_to_your_data')  # Update with your actual data path

    # Initialize the embedding model
    embed_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": DEVICE}
    )

    # Initialize the language model
    llm = Groq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1024,
        top_p=1,
        stream=False
    )

    # Set global settings
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
    Settings.num_output = 2048
    Settings.context_window = 4000

    # Create the index
    index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)

    # Store the index in the app state for later use
    app.state.index = index

    yield

    # Shutdown code: Release resources here if necessary

def get_query_engine(app: FastAPI = Depends()):
    return app.state.index.as_query_engine()
