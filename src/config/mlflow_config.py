import mlflow
from threading import Lock

class MetricsCollector:
    def __init__(self):
        self.metrics = {}
        self.model = None
        self.lock = Lock()
    
    def add_metric(self, key, value, model=None):
        with self.lock:
            self.metrics[key] = value
            print(self.metrics)
            global dict
            dict = self.metrics
            if model:
                self.model = model
    
    def log_all(self):
        with self.lock:
            print("Metrics before logging:", self.metrics)
        """Log all collected metrics at once"""
        try:
            mlflow.set_tracking_uri("http://127.0.0.1:8080")
            
            # Attempt to create the experiment (ignore if it already exists)
            try:
                mlflow.create_experiment("ASK_RC")
            except Exception:
                pass
            
            mlflow.set_experiment("ASK_RC")
            
            with mlflow.start_run():
                # Log all collected metrics
                print("*****************************************************************\n",dict)
                mlflow.log_metrics(dict)
                if self.model:
                    mlflow.sklearn.log_model(self.model, "Model")
            
            # Clear the collections after logging
            self.metrics = {}
            self.model = None
        except Exception as e:
            print(f"MLflow logging failed: {str(e)}")


'''
# Usage example:
collector = MetricsCollector()

# Add metrics without logging
collector.add_metric("accuracy", 0.95)
collector.add_metric("loss", 0.1)
collector.add_metric("precision", 0.92)

# Log everything at once when ready
collector.log_all()
'''