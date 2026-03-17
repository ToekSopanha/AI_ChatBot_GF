"""
💬 Sentiment Analyzer — Use your trained ML model
Run predict.py to analyze text emotions in real-time
"""

import joblib
import numpy as np
from pathlib import Path

MODEL_PATH = "sentiment_model.pkl"

EMOJIS = {
    "positive": "😊",
    "negative": "😞",
    "neutral":  "😐",
}

COLORS = {
    "positive": "\033[92m",   # green
    "negative": "\033[91m",   # red
    "neutral":  "\033[94m",   # blue
}
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"


def load_model():
    if not Path(MODEL_PATH).exists():
        print(f"\n❌  Model not found! Run  python train_model.py  first.\n")
        return None
    return joblib.load(MODEL_PATH)


def analyze(model, text: str) -> dict:
    proba = model.predict_proba([text])[0]
    classes = model.classes_
    label = classes[np.argmax(proba)]
    confidence = np.max(proba) * 100
    scores = {c: round(p * 100, 1) for c, p in zip(classes, proba)}
    return {"label": label, "confidence": confidence, "scores": scores}


def print_result(text: str, result: dict):
    label = result["label"]
    conf  = result["confidence"]
    emoji = EMOJIS[label]
    color = COLORS[label]
    scores = result["scores"]

    print(f"\n  {'─'*46}")
    print(f"  📝  {DIM}{text[:80]}{RESET}")
    print(f"  {'─'*46}")
    print(f"  Result:  {color}{BOLD}{label.upper()}  {emoji}{RESET}   "
          f"({conf:.1f}% confident)")
    print()

    # Score bars
    bar_max = 20
    for lbl in ["positive", "neutral", "negative"]:
        pct = scores.get(lbl, 0)
        filled = int(pct / 100 * bar_max)
        bar = "█" * filled + "░" * (bar_max - filled)
        c = COLORS[lbl]
        print(f"  {lbl:10s}  {c}{bar}{RESET}  {pct:5.1f}%")
    print(f"  {'─'*46}\n")


def print_banner():
    print()
    print(YELLOW + "  ╔══════════════════════════════════════════╗")
    print(YELLOW + "  ║" + RESET + BOLD + "   🧠  Sentiment Analyzer — Your ML Model  " + RESET + YELLOW + "║")
    print(YELLOW + "  ╚══════════════════════════════════════════╝" + RESET)
    print()
    print(DIM + "  Type any text and the AI will detect the emotion.")
    print(DIM + "  Type  /quit  to exit   |   /batch  for bulk mode" + RESET)
    print()


def batch_mode(model):
    """Analyze multiple lines at once"""
    print(f"\n  {DIM}Paste multiple lines of text. Type  /done  when finished.{RESET}\n")
    lines = []
    while True:
        try:
            line = input(f"  {CYAN}>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() == "/done":
            break
        if line:
            lines.append(line)

    if not lines:
        return

    print(f"\n  Analyzing {len(lines)} texts...\n")
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for line in lines:
        result = analyze(model, line)
        print_result(line, result)
        counts[result["label"]] += 1

    # Summary
    print(f"  {'═'*46}")
    print(f"  📊  Batch Summary ({len(lines)} texts):")
    for lbl, count in counts.items():
        emoji = EMOJIS[lbl]
        color = COLORS[lbl]
        print(f"     {color}{lbl:10s}{RESET}  {emoji}  {count} texts")
    print(f"  {'═'*46}\n")


def main():
    model = load_model()
    if not model:
        return

    print_banner()
    print(f"  ✅  Model loaded successfully!\n")

    while True:
        try:
            user_input = input(f"  {CYAN}{BOLD}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  Goodbye! 👋\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            print(f"\n  Goodbye! 👋\n")
            break

        if user_input.lower() == "/batch":
            batch_mode(model)
            continue

        result = analyze(model, user_input)
        print_result(user_input, result)


if __name__ == "__main__":
    main()