import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import uvicorn
from src.core.database import init_db
from src.api.websocket import router as websocket_router

# We import the router we built in the previous step
from src.api.routes import router as api_v1_router

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
    """
    Enterprise lifespan manager. 
    Code before the 'yield' runs exactly once during server boot.
    Code after the 'yield' runs exactly once during server shutdown.
    """
    global redis_client
    await init_db()
    logger.info("Initializing high-performance Fraud Detection Gateway...")
    
    try:
        # Initialize Redis connection pool for rate-limiting and fast feature lookups
        # In a real environment, the URL comes from an environment variable.
        redis_client = redis.from_url(
            "redis://localhost:6379", 
            encoding="utf-8", 
            decode_responses=True,
            max_connections=100
        )
        # Ping to verify the connection is actually alive before accepting API traffic
        await redis_client.ping()
        logger.info("Redis connection pool established successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis. Rate limiting will be disabled. Error: {e}")
        # Note: Depending on strictness, you might raise an exception here to crash the server 
        # if Redis is deemed absolutely mandatory for business logic.

    # Yield control back to FastAPI to start accepting HTTP requests
    yield 

    # --- SHUTDOWN SEQUENCE ---
    logger.info("Initiating graceful shutdown sequence...")
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection pool closed safely.")

# Instantiate the main FastAPI application
app = FastAPI(
    title="Fintech Fraud Detection API",
    description="High-throughput, low-latency ML inference gateway.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None # Disable redoc to save static file loading overhead
)

# Enforce strict CORS Security
# If your React frontend is running on localhost:3000, only allow that exact origin.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173", # Standard Vite port
    # "https://admin.yourfintech.com" # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"], # Only allow POST for transactions
    allow_headers=["Authorization", "Content-Type"],
)

# Mount our modular API router
app.include_router(api_v1_router)

@app.get("/health", tags=["System"])
async def health_check():
    """Load Balancer health check endpoint."""
    return {"status": "healthy", "service": "fraud_gateway_v1"}

# Allow executing the file directly for local development
if __name__ == "__main__":
    logger.info("Starting Uvicorn ASGI server...")
    # workers=1 for local dev. In production, workers = number of CPU cores.
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True, workers=1)