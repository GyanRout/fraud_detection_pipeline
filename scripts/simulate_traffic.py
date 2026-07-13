import time
import random
import requests
from datetime import datetime, timezone

# Target API Endpoint
API_URL = "http://localhost:8000/api/v1/transactions/score"

def generate_payload(is_fraud: bool) -> dict:
    """Generates synthetic transaction payloads based on requested risk profile."""
    
    # Legit profiles: Low amounts, low velocity, low device risk
    if not is_fraud:
        amount = round(random.uniform(5.0, 150.0), 2)
        velocity = random.randint(0, 2)
        device_risk = round(random.uniform(0.01, 0.20), 3)
    
    # Fraud profiles (Card Testing/Account Takeover): High amounts, rapid velocity, risky devices
    else:
        amount = round(random.uniform(500.0, 2500.0), 2)
        velocity = random.randint(5, 15)
        device_risk = round(random.uniform(0.70, 0.99), 3)

    return {
        "transaction_id": f"tx_{int(time.time() * 1000)}_{random.randint(100,999)}",
        "user_id": f"usr_{random.randint(1000, 9999)}",
        "amount": amount,
        "velocity_1h": velocity,
        "device_risk_score": device_risk,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def run_simulation(num_requests=20):
    print("🚀 Starting Fraud Traffic Simulation...")
    print(f"Targeting: {API_URL}\n")
    
    success_count = 0
    
    for i in range(num_requests):
        # 20% chance to generate a highly anomalous fraud transaction
        is_fraud = random.random() < 0.20 
        payload = generate_payload(is_fraud)
        
        try:
            # Measure round-trip time from the client side
            start_time = time.time()
            response = requests.post(API_URL, json=payload, timeout=2.0)
            rtt_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                action = data.get("action")
                score = data.get("risk_score")
                api_latency = data.get("latency_ms")
                
                print(f"[{i+1}/{num_requests}] 💸 TX: ${payload['amount']:<7.2f} | "
                      f"Action: {action:<7} | Score: {score:.3f} | "
                      f"API Latency: {api_latency:.2f}ms | Client RTT: {rtt_ms:.2f}ms")
                success_count += 1
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("🛑 Connection refused. Is the FastAPI server running?")
            break
            
        # Sleep randomly between 0.5 and 2 seconds to simulate organic traffic
        time.sleep(random.uniform(0.5, 2.0))

    print(f"\n✅ Simulation Complete. {success_count}/{num_requests} requests processed.")

if __name__ == "__main__":
    run_simulation()