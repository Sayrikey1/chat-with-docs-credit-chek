# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from config.database import engine
from models import models
from routers import auth, chatbot
from rag.query_engine import lifespan

# Load environment variables
load_dotenv()

# Initialize the FastAPI application with the lifespan context manager
app = FastAPI(lifespan=lifespan)

# Create all database tables
models.Base.metadata.create_all(bind=engine)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust the origins to restrict access as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chatbot.router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}
