from typing import Any
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings, VectorStoreIndex
from llama_index.llms.groq import Groq
from llama_index.readers.web import SimpleWebPageReader
from langchain_huggingface import HuggingFaceEmbeddings
import logging
import torch
import os
from rag.data.extractions import extractions

import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler("app.log")  # Also log to a file
    ]
)

logger = logging.getLogger("rag_engine")

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        start_time = time.time()

        # Load documents using SimpleWebPageReader
        logger.info("Starting document extraction")
        reader = SimpleWebPageReader(html_to_text=True)
        docs = reader.load_data(extractions)
        logger.info(f"Document extraction completed: {len(docs)} documents loaded")
        
        # Initialize the embedding model
        logger.info("Initializing embedding model")
        embed_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={"device": DEVICE}
        )
        logger.info("Embedding model initialization completed")

        # Initialize the language model
        logger.info("Initializing language model")
        llm = Groq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        logger.info("Language model initialization completed")

        # Set global settings
        logger.info("Configuring global settings")
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
        Settings.num_output = 2048
        Settings.context_window = 4000
        logger.info("Global settings configured")

        # Create the index
        logger.info("Creating vector index from documents")
        index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)
        logger.info("Vector index creation completed")

        # Store the index in the app state for later use
        app.state.index = index
        logger.info("Application startup complete")


        elapsed = time.time() - start_time
        logger.info(f"Operation completed in {elapsed:.2f} seconds") 


        yield

        # Shutdown code
        logger.info("Application shutting down")
    except Exception as e:
        logger.error(f"Error during application lifecycle: {str(e)}", exc_info=True)
        raise e

def get_query_engine(request: Request):
    logger.debug("Query engine requested")
    return request.app.state.index.as_query_engine()