# Standard library imports
from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Any

# Third-party imports
from fastapi import FastAPI, Request
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
import torch

# llama_index imports (third-party but from the same package, grouped together)
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.groq import Groq
from llama_index.readers.web import SimpleWebPageReader
from llama_index.vector_stores.pinecone import PineconeVectorStore

# Local or project-specific imports
from rag.data.extractions import extractions


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

# Vector database configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "rag-documents"
NAMESPACE = "web-extractions"

def initialize_vector_db():
    """Initialize Pinecone and create index if it doesn't exist"""
    try:
        logger.info("Initializing Pinecone")
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Check if index exists, if not create it
        if INDEX_NAME not in pc.list_indexes().names():
            logger.info(f"Creating new index: {INDEX_NAME}")
            pc.create_index(
                name=INDEX_NAME,
                dimension=768,  # Dimension for all-mpnet-base-v2
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            logger.info(f"Index {INDEX_NAME} created successfully")
        else:
            logger.info(f"Index {INDEX_NAME} already exists")
            
        return pc.Index(INDEX_NAME)
    except Exception as e:
        logger.error(f"Error initializing Pinecone: {str(e)}", exc_info=True)
        raise e

def load_or_create_index(docs=None, embed_model=None, force_reload=False):
    """Load index from vector DB or create if needed"""
    try:
        # Initialize Pinecone
        pinecone_index = initialize_vector_db()
        stats = pinecone_index.describe_index_stats()
        vector_count = stats.total_vector_count
        
        # If the index is empty or force reload is True, create and populate it
        if vector_count == 0 or force_reload:
            if docs is None or embed_model is None:
                raise ValueError("Documents and embed_model must be provided for initial indexing")
                
            logger.info("Creating new vector store index")
            # Create Pinecone vector store
            vector_store = PineconeVectorStore(
                pinecone_index=pinecone_index,
                namespace=NAMESPACE
            )
            
            # Create the index from documents
            index = VectorStoreIndex.from_documents(
                docs, 
                vector_store=vector_store,
                embed_model=embed_model
            )
            
            logger.info(f"Vector index successfully created with {len(docs)} documents")
            return index
        else:
            # Load existing index
            logger.info(f"Loading existing index with {vector_count} vectors")
            vector_store = PineconeVectorStore(
                pinecone_index=pinecone_index,
                namespace=NAMESPACE
            )
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=embed_model
            )
            logger.info("Vector index successfully loaded from Pinecone")
            return index
    except Exception as e:
        logger.error(f"Error in load_or_create_index: {str(e)}", exc_info=True)
        raise e

global_index = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_index
    try:
        start_time = time.time()
        
        # If we already have a global index from a previous reload, use it
        if global_index is not None and os.getenv("FORCE_RELOAD_INDEX", "false").lower() != "true":
            logger.info("Using existing index from previous server instance")
            app.state.index = global_index
            logger.info("Application startup completed (using cached index)")
            yield
            return
        
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

        # Check if we need to load documents and build index
        force_reload = os.getenv("FORCE_RELOAD_INDEX", "false").lower()
        if force_reload == "true":
            logger.info("Force reload requested. Loading documents...")
            reader = SimpleWebPageReader(html_to_text=True)
            docs = reader.load_data(extractions)
            logger.info(f"Document extraction completed: {len(docs)} documents loaded")
            
            # Create or update the index
            index = load_or_create_index(docs=docs, embed_model=embed_model, force_reload=True)
        else:
            # Just load the existing index
            index = load_or_create_index(embed_model=embed_model)

        # Store the index in the app state and in global variable
        app.state.index = index
        global_index = index
        
        elapsed = time.time() - start_time
        logger.info(f"Application startup completed in {elapsed:.2f} seconds")

        yield

        # Shutdown code
        logger.info("Application shutting down")
    except Exception as e:
        logger.error(f"Error during application lifecycle: {str(e)}", exc_info=True)
        raise e

def get_query_engine(request: Request):
    logger.debug("Query engine requested")
    return request.app.state.index.as_query_engine()