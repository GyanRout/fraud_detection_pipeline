import os
import logging
import torch
import numpy as np

# Configure basic logging for the ML engine
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FraudInferenceEngine:
    """
    Singleton serving engine for the TorchScript fraud detection model.
    Ensures the model is loaded into RAM exactly once across all async workers.
    """
    _instance = None
    _is_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FraudInferenceEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if the singleton is instantiated multiple times
        if self._is_initialized:
            return
            
        self._load_model()
        self._load_scaler_params()
        self._is_initialized = True

    def _load_model(self):
        """Loads the compiled C++ graph and warms up the execution engine."""
        model_path = os.getenv("MODEL_PATH", "models/fraud_model_traced.pt")
        
        if not os.path.exists(model_path):
            logger.error(f"Model artifact not found at {model_path}.")
            raise FileNotFoundError(f"Missing model artifact: {model_path}")
            
        logger.info(f"Loading TorchScript model from {model_path} into CPU memory...")
        
        # We explicitly map to CPU. Inference APIs scale horizontally across cheaper CPU instances.
        self.model = torch.jit.load(model_path, map_location=torch.device('cpu'))
        self.model.eval()

        # WARM-UP: JIT compilation optimizes the graph on the very first forward pass.
        # We run a dummy tensor through it now so the first actual API user doesn't experience a latency spike.
        logger.info("Warming up the computational graph...")
        dummy_input = torch.randn(1, 5)
        with torch.no_grad():
            self.model(dummy_input)
            
        logger.info("Inference engine ready.")

    def _load_scaler_params(self):
        """
        Loads statistical boundaries for feature scaling.
        In a microservices architecture, do not import scikit-learn in your inference path.
        It is too heavy. We use purely mathematical scaling via NumPy.
        """
        # Feature order: [amount, velocity_1h, time_sin, time_cos, device_risk_score]
        # In a real system, fetch these from Redis or MLflow. Here, we use estimations from our synthetic data.
        self.means = np.array([55.0, 1.2, 0.0, 0.0, 0.25], dtype=np.float32)
        self.scales = np.array([60.0, 1.5, 0.707, 0.707, 0.15], dtype=np.float32)

    def predict(self, features: list[float]) -> float:
        """
        Executes a sub-millisecond forward pass.
        Returns a float between 0.0 (Legitimate) and 1.0 (Fraud).
        """
        # 1. Vectorized Scaling
        # Z-Score Normalization: z = (x - mean) / scale
        raw_array = np.array(features, dtype=np.float32)
        scaled_features = (raw_array - self.means) / self.scales
        
        # 2. Zero-Copy Tensor Creation
        # torch.from_numpy shares the underlying memory buffer with the NumPy array.
        # This is strictly faster than torch.tensor(), which triggers a memory copy.
        input_tensor = torch.from_numpy(scaled_features).unsqueeze(0)
        
        # 3. Model Execution
        with torch.no_grad():
            risk_score = self.model(input_tensor).item()
            
        return risk_score

# Instantiate immediately so it's ready when the module is imported by FastAPI
inference_engine = FraudInferenceEngine()