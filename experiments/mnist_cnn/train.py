#!/usr/bin/env python3
"""MNIST CNN — demo experiment for Tao pipeline validation."""
import json
import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

TASK_ID = os.environ.get("TASK_ID", "mnist_cnn")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/workspace/results")
EPOCHS = 5
BATCH_SIZE = 128
LR = 0.01

os.makedirs(RESULTS_DIR, exist_ok=True)

# Write PID file
pid_file = os.path.join(RESULTS_DIR, f"{TASK_ID}.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

print(f"[{TASK_ID}] Starting MNIST CNN training on {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Data
transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
train_data = datasets.MNIST("/workspace/data", train=True, download=True, transform=transform)
test_data = datasets.MNIST("/workspace/data", train=False, transform=transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
test_loader = DataLoader(test_data, batch_size=1000, num_workers=2)

# Model
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.25)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.dropout(x)
        x = torch.flatten(x, 1)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)

model = SimpleCNN().to(device)
optimizer = optim.Adam(model.parameters(), lr=LR)
criterion = nn.CrossEntropyLoss()

start_time = time.time()

# Train
for epoch in range(1, EPOCHS + 1):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += len(target)

    train_acc = correct / total
    avg_loss = total_loss / len(train_loader)

    # Evaluate
    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            pred = output.argmax(dim=1)
            test_correct += pred.eq(target).sum().item()
            test_total += len(target)
    test_acc = test_correct / test_total

    elapsed = time.time() - start_time
    print(f"Epoch {epoch}/{EPOCHS} — loss={avg_loss:.4f} train_acc={train_acc:.4f} test_acc={test_acc:.4f} elapsed={elapsed:.1f}s")

    # Write progress file (Tao protocol)
    progress = {
        "task_id": TASK_ID,
        "epoch": epoch,
        "total_epochs": EPOCHS,
        "loss": avg_loss,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "elapsed_sec": elapsed,
    }
    progress_file = os.path.join(RESULTS_DIR, f"{TASK_ID}_PROGRESS.json")
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)

# Save model
torch.save(model.state_dict(), os.path.join(RESULTS_DIR, "model.pt"))

# Final results
total_time = time.time() - start_time
results = {
    "task_id": TASK_ID,
    "status": "success",
    "epochs": EPOCHS,
    "final_test_acc": test_acc,
    "final_train_acc": train_acc,
    "final_loss": avg_loss,
    "total_time_sec": total_time,
    "device": str(device),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
}
print(f"\n[{TASK_ID}] Training complete: test_acc={test_acc:.4f} in {total_time:.1f}s")

# Write result file
with open(os.path.join(RESULTS_DIR, f"{TASK_ID}_result.json"), "w") as f:
    json.dump(results, f, indent=2)

# Write DONE marker (Tao protocol)
with open(os.path.join(RESULTS_DIR, f"{TASK_ID}_DONE"), "w") as f:
    json.dump(results, f, indent=2)

# Clean up PID file
os.remove(pid_file)
print(f"[{TASK_ID}] DONE marker written. Experiment complete.")
