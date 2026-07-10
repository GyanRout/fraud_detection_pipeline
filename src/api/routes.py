import time
import logging
from fastapi import APIRouter, HTTPException, status
from src.schemas.transaction import TransactionRequest, TransactionResponse
from src.ml.inference import inference_engine
from fastapi import BackgroundTasks
from src.core.database import log_transaction_to_db
from src.api.websocket import alert_manager

# Initialize standard structured logger for API traffic
logger = logging.getLogger("api_v1_routes")

# Create an APIRouter instance to modularize endpoints
router = APIRouter(prefix="/api/v1", tags=["Transactions"])

# Hyperparameters for business logic thresholds
REVIEW_THRESHOLD = 0.50
BLOCK_THRESHOLD = 0.80

@router.post(
    "/transactions/score", 
    response_model=TransactionResponse, 
    status_code=status.HTTP_200_OK,
    summary="Score a financial transaction for real-time fraud risk"
)
async def score_transaction(payload: TransactionRequest, background_tasks: BackgroundTasks) -> TransactionResponse:
    """
    High-throughput async endpoint to evaluate transaction risk.
    Validates payload against TransactionRequest, passes elements to the TorchScript
    inference engine, applies threshold rules, and returns a TransactionResponse contract.
    """
    # 1. Start High-Precision Timer
    # time.perf_counter() measures system execution time down to nanoseconds
    start_time = time.perf_counter()
    
    try:
        # 2. Feature Extraction & Ordering
        # Order MUST exactly match what the model was trained on:
        # [amount, velocity_1h, time_sin, time_cos, device_risk_score]
        
        # Calculate cyclical time coordinates on the fly using the request's timestamp
        tx_datetime = payload.timestamp
        hour = tx_datetime.hour + (tx_datetime.minute / 60.0)
        import numpy as np # Import locally if needed to isolate dependency footprints
        time_sin = float(np.sin(2 * np.pi * hour / 24.0))
        time_cos = float(np.cos(2 * np.pi * hour / 24.0))
        
        features = [
            payload.amount,
            float(payload.velocity_1h),
            time_sin,
            time_cos,
            payload.device_risk_score
        ]
        
        # 3. Model Inference execution (CPU-bound but isolated within C++ graph)
        risk_score = inference_engine.predict(features)
        
        # 4. Deterministic Rule-Based Threshold Mapping
        if risk_score >= BLOCK_THRESHOLD:
            action = "BLOCK"
        elif risk_score >= REVIEW_THRESHOLD:
            action = "REVIEW"
        else:
            action = "APPROVE"
            
        # 5. Stop Timer & Compute API Latency
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0
        
        # 6. Structured logging for analytics ingestion (e.g., Vector/Splunk)
        logger.info(
            f"TX_ID: {payload.transaction_id} | USER: {payload.user_id} | "
            f"SCORE: {risk_score:.4f} | ACTION: {action} | LATENCY: {latency_ms:.2f}ms"
        )

        background_tasks.add_task(
        log_transaction_to_db,
        tx_id=payload.transaction_id,
        user_id=payload.user_id,
        amount=payload.amount,
        velocity=payload.velocity_1h,
        device_risk=payload.device_risk_score,
        risk_score=risk_score,
        action=action,
        latency=latency_ms
        )

        if action in ["BLOCK", "REVIEW"]:
            background_tasks.add_task(
                alert_manager.broadcast_alert,
                {
                    "transaction_id": payload.transaction_id,
                    "amount": payload.amount,
                    "action": action,
                    "risk_score": round(risk_score, 4),
                    "timestamp": str(payload.timestamp)
                }
            )
        
        # 7. Construct and return response contract
        return TransactionResponse(
            transaction_id=payload.transaction_id,
            risk_score=risk_score,
            action=action,
            latency_ms=round(latency_ms, 3)
        )
        
    except Exception as e:
        # Unhandled execution traps must never leak core tracebacks to the client.
        # Log the full exception locally for engineering triage, return clean 500.
        logger.error(f"Critical error processing TX {payload.transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal execution error processing risk assessment."
        )