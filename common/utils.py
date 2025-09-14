import os
import json
from datetime import datetime
from typing import Dict, Any

def utc_timestamp():
    return datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")

def make_run_dir(base_dir: str) -> str:
    run_dir = os.path.join(base_dir, "runs", utc_timestamp())
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

def load_config(project_root: str) -> Dict[str, Any]:
    cfg_path = os.path.join(project_root, "config.json")
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Missing config.json at {cfg_path}. Copy config.example.json and fill in your keys.")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def update_history(project_root: str, entry: Dict[str, Any]):
    hist_path = os.path.join(project_root, "history.json")
    history = []
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception:
                history = []
    history.append(entry)
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)