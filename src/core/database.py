import os
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Float, DateTime, Integer

logger = logging.getLogger("fraud_database_layer")

# 1. Async Engine & Session Pool Configuration
# In production, this comes from a secure .env file or AWS Secrets Manager.
# We use postgresql+asyncpg to ensure non-blocking I/O operations.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/fraud_db"
)

# The Engine is the core factory for database connections.
# pool_size: Number of permanent connections to keep open.
# max_overflow: Extra connections allowed during sudden traffic spikes.
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, # Set to True to print raw SQL during local debugging
    pool_size=20, 
    max_overflow=10
)

# The AsyncSession factory generates ephemeral sessions for individual transactions.
# expire_on_commit=False prevents SQLAlchemy from querying the DB again after a commit.
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# 2. ORM Data Model (PostgreSQL Table Schema)
class TransactionRecord(Base):
    """
    SQLAlchemy ORM Model representing the 'transactions' table in PostgreSQL.
    This stores the immutable audit trail of every API evaluation.
    """
    __tablename__ = "transactions"

    # We use the incoming transaction_id as the Primary Key for O(1) lookups
    transaction_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    velocity_1h = Column(Integer, nullable=False)
    device_risk_score = Column(Float, nullable=False)
    
    # ML Engine Outputs
    risk_score = Column(Float, nullable=False)
    action = Column(String(20), index=True, nullable=False)
    latency_ms = Column(Float, nullable=False)
    
    # Audit Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

# 3. Asynchronous Database Workers
async def init_db():
    """
    Creates tables if they don't exist. 
    NOTE: In an enterprise environment, NEVER use this in production. 
    You must use a migration tool like Alembic to manage schema changes.
    This is strictly for local bootstrapping.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL database tables verified/created.")

async def log_transaction_to_db(
    tx_id: str, 
    user_id: str, 
    amount: float, 
    velocity: int, 
    device_risk: float, 
    risk_score: float, 
    action: str, 
    latency: float
):
    """
    Background worker function to persist transaction audits.
    This is designed to be fired asynchronously AFTER the API responds to the client.
    """
    # Use an async context manager to ensure the DB connection is released back to the pool
    async with AsyncSessionLocal() as session:
        try:
            new_record = TransactionRecord(
                transaction_id=tx_id,
                user_id=user_id,
                amount=amount,
                velocity_1h=velocity,
                device_risk_score=device_risk,
                risk_score=risk_score,
                action=action,
                latency_ms=latency
            )
            session.add(new_record)
            
            # Flush and commit the transaction to disk
            await session.commit()
            logger.debug(f"Successfully persisted TX {tx_id} to PostgreSQL.")
            
        except Exception as e:
            # We must rollback to prevent the session pool from getting corrupted with failed states
            await session.rollback()
            logger.error(f"FATAL: Database persistence failed for TX {tx_id}. Error: {str(e)}")