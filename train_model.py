import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Load dataset
df = pd.read_csv("athlete_data.csv")

# Features and target
X = df.drop("risk", axis=1)
y = df["risk"]

# Train model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

# Create model folder if not exists
if not os.path.exists("model"):
    os.makedirs("model")

# Save model
joblib.dump(model, "model/doping_model.pkl")

print("Model trained successfully!")
print("doping_model.pkl created.")