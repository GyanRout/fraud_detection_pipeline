import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import uvicorn

# Import our modular routers and database initializer
from src.api.routes import router as api_v1_router
from src.api.websocket import router as websocket_router
from src.core.database import init_db

# Configure global application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("fraud_gateway_main")

# Global placeholder for our Redis Connection Pool
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    logger.info("Initializing high-performance Fraud Detection Gateway...")
    
    # 1. Initialize PostgreSQL Database Tables
    await init_db()
    
    try:
        # 2. Initialize Redis connection pool
        redis_client = redis.from_url(
            "redis://localhost:6379", 
            encoding="utf-8", 
            decode_responses=True,
            max_connections=100
        )
        await redis_client.ping()
        logger.info("Redis connection pool established successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis. Error: {e}")

    # Yield control back to FastAPI to start accepting HTTP/WebSocket requests
    yield 

    # --- SHUTDOWN SEQUENCE ---
    logger.info("Initiating graceful shutdown sequence...")
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection pool closed safely.")

# Instantiate the main FastAPI application
app = FastAPI(
    title="Fintech Fraud Detection API",
    version="1.0.0",
    lifespan=lifespan,
    redoc_url=None
)

# BULLETPROOF CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Exact React dev server origin
        "http://127.0.0.1:5173",  # Loopback variant
        "http://localhost:3000"   # Standard React port backup
    ],
    allow_credentials=True,
    allow_methods=["*"],          # Explicitly allow ALL methods
    allow_headers=["*"],          # Explicitly allow ALL headers
)

# Mount our modular routers
app.include_router(api_v1_router)
app.include_router(websocket_router)

@app.get("/health", tags=["System"])
async def health_check():
    """Load Balancer health check endpoint."""
    return {"status": "healthy", "service": "fraud_gateway_v1"}

# Allow executing the file directly for local development
if __name__ == "__main__":
    logger.info("Starting Uvicorn ASGI server...")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True, workers=1)