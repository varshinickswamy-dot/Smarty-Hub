from sklearn.tree import DecisionTreeClassifier
import joblib
from pathlib import Path

X = [[40],[55],[70],[85]]
y = ["ITI","Diploma","Engineering","Medical"]

model = DecisionTreeClassifier(random_state=42)
model.fit(X,y)

joblib.dump(model, Path(__file__).with_name("career_model.pkl"))
print("Model trained")