# 🛡️ High-Throughput Fraud Inference Gateway

An end-to-end, sub-millisecond Machine Learning pipeline designed for real-time financial fraud detection. This project demonstrates enterprise-grade ML system architecture, completely decoupling compute-bound neural network inference from I/O-bound network/database operations.

## 🚀 Architectural Highlights

Most machine learning portfolios stop at the Jupyter Notebook. This project was built to simulate a production-grade Tier-1 financial system, focusing on latency, concurrency, and real-time event streaming.

*   **Bypassing the Python GIL:** The PyTorch Multilayer Perceptron (MLP) was compiled down to a static C++ graph using TorchScript. Combined with zero-copy memory operations, this achieves deterministic sub-millisecond inference (~0.8ms) on a single CPU core.
*   **Algorithmic Imbalance Handling:** Instead of synthesizing fake financial data with SMOTE, the network utilizes **Focal Loss** to dynamically scale down the loss of confident predictions, forcing the optimizer to strictly learn the hard, misclassified anomalous transactions.
*   **Asynchronous I/O & Background Tasks:** Database writes to PostgreSQL are handled via `asyncpg` and FastAPI Background Tasks. The system responds to the payment client in <1ms and persists the audit log asynchronously, preventing I/O bottlenecks.
*   **Stateful Real-Time Broadcasting:** Built a custom WebSocket Connection Manager to stream flagged transactions (Blocks/Reviews) to a React Admin Dashboard in real-time. Includes defensive garbage collection for dead client sockets.

## 🛠️ Tech Stack

*   **Machine Learning:** PyTorch, TorchScript, Focal Loss, Scikit-Learn
*   **Backend Gateway:** Python, FastAPI, Pydantic (Rust-based validation), Uvicorn
*   **Infrastructure:** Docker, PostgreSQL ( `asyncpg` ), Redis
*   **Frontend Operations UI:** React, Vite, Tailwind CSS, Lucide Icons

## ⚙️ System Components

1.  `models/` : Contains the compiled `fraud_model_traced.pt` C++ artifact.
2.  `src/ml/inference.py` : The singleton inference engine that warms up the JIT compiler and executes zero-copy tensor evaluations.
3.  `src/core/database.py` : SQLAlchemy 2.0 ORM and asynchronous connection pooling.
4.  `src/api/websocket.py` : Thread-safe broadcaster for real-time threat ledgers.
5.  `frontend/` : The stateful React dashboard visualizing network anomalies.

## 🚦 Local Deployment

Ensure you have Docker and Node.js installed.

**1. Start the Infrastructure (PostgreSQL & Redis)**

```bash
docker-compose up -d
```

**2. Boot the High-Performance API**
```bash
python -m venv .venv
source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -r requirements.txt
uvicorn src.main:app --reload
```

**3. Launch the React Dashboard**
```bash
cd frontend
npm install
npm run dev
```

**4. Run the Traffic Simulator In a separate terminal, generate synthetic financial traffic to watch the pipeline in action:**
```bash
python scripts/simulate_traffic.py
```
