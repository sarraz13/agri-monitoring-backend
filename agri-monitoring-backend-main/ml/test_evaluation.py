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

# Optional: Plot normal vs anomalies
plt.figure(figsize=(10,6))
# Scatter plot: X-axis = sample index, Y-axis = soil moisture, Color = prediction
plt.scatter(range(len(X_test)), X_test[:,0], c=y_pred, cmap='coolwarm', label='Predicted Anomalies')
plt.xlabel('Sample Index')
plt.ylabel('Soil Moisture (%)')
plt.title('ML Model Prediction (Red = Anomaly, Blue = Normal)')
plt.legend()
plt.tight_layout()
# Save plot for documentation/report
plt.savefig('evaluation_plot.png')  # Save plot for report
plt.show() #show plot