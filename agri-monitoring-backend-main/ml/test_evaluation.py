import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score, f1_score
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
MODEL EVALUATION SCRIPT
Tests the trained ML model with synthetic data.
Calculates precision, recall, F1-score and creates visualizations.
"""

from ml_model import MLModel
# Load the trained model
ml_model = MLModel()

# Generate synthetic test data
np.random.seed(42)

# Normal readings
X_normal = np.column_stack([
    np.random.normal(60, 5, 200),
    np.random.normal(24, 3, 200),
    np.random.normal(65, 8, 200)
])

# Anomalous readings
X_anomaly = np.column_stack([
    np.random.uniform(20, 40, 50),
    np.random.uniform(32, 40, 50),
    np.random.uniform(20, 40, 50)
])

# Combine
X_test = np.vstack([X_normal, X_anomaly])
y_true = np.array([0]*200 + [1]*50)  # 0 = normal, 1 = anomaly

# Predict anomalies
y_pred = []
for row in X_test:
    is_anomaly, score = ml_model.predict(*row)
    y_pred.append(int(is_anomaly))
y_pred = np.array(y_pred)

# Calculate metrics
precision = precision_score(y_true, y_pred)
recall = recall_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred)

print("===== Evaluation Metrics =====")
print(f"Precision: {precision:.2f}")
print(f"Recall: {recall:.2f}")
print(f"F1-score: {f1:.2f}")

# Create a more informative visualization
fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

# Main prediction plot
colors = ['blue' if pred == 0 else 'red' for pred in y_pred]
ax1.scatter(range(len(X_test)), X_test[:, 0], c=colors, alpha=0.6, s=30)
ax1.axvline(x=199.5, color='green', linestyle='--', alpha=0.5, label='Normal/Anomaly Boundary')
ax1.set_xlabel('Sample Index')
ax1.set_ylabel('Soil Moisture (%)')
ax1.set_title('Model Predictions (0-199: Normal, 200-249: Anomaly)')
ax1.legend()
ax1.grid(True, alpha=0.3)

plt.savefig('detailed_evaluation_plot.png', dpi=150, bbox_inches='tight')
plt.show()