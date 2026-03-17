"""
🧠 Sentiment Analysis — Trained on Kaggle Sentiment140
1.6 Million real tweets dataset → way smarter model!
"""

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.pipeline import Pipeline
import re

# ── Config ────────────────────────────────────────────────────────────────────
DATASET_FILE = "training.1600000.processed.noemoticon.csv"
SAMPLE_SIZE  = 100_000   # use 100k tweets (increase for more accuracy, decrease for speed)

# ── Text Cleaner ──────────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"[^a-z0-9\s!?'.,]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ── Load Kaggle Dataset ───────────────────────────────────────────────────────
def load_data():
    path = Path(DATASET_FILE)
    if not path.exists():
        print(f"\n❌  Dataset not found!")
        print(f"    Make sure '{DATASET_FILE}'")
        print(f"    is in the same folder as this script.\n")
        print(f"    Download from: kaggle.com/datasets/kazanova/sentiment140\n")
        exit(1)

    print(f"📂  Loading dataset...")
    df = pd.read_csv(
        path,
        encoding="latin-1",
        header=None,
        names=["label", "id", "date", "query", "user", "text"]
    )

    df["label"] = df["label"].map({0: "negative", 4: "positive"})
    df = df[["text", "label"]].dropna()

    print(f"✅  Loaded {len(df):,} total tweets")
    print(f"⚡  Sampling {SAMPLE_SIZE:,} tweets for training...")

    half = SAMPLE_SIZE // 2
    pos = df[df["label"] == "positive"].sample(half, random_state=42)
    neg = df[df["label"] == "negative"].sample(half, random_state=42)
    df = pd.concat([pos, neg]).sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"🧹  Cleaning text...")
    df["text"] = df["text"].apply(clean_text)
    df = df[df["text"].str.len() > 3]

    return df

# ── Train ─────────────────────────────────────────────────────────────────────
def train():
    print("\n" + "="*52)
    print("  🧠  Sentiment Analysis — Kaggle Edition")
    print("="*52 + "\n")

    df = load_data()

    print(f"\n📊  Dataset: {len(df):,} samples")
    print(df["label"].value_counts().to_string())

    X = df["text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n✂️   Train: {len(X_train):,} | Test: {len(X_test):,}")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=100_000,
            sublinear_tf=True,
            min_df=2,
            strip_accents="unicode",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=1.0,
            solver="lbfgs",
            n_jobs=-1,
        )),
    ])

    print("\n⚙️   Training model (this may take 1-2 minutes)...")
    pipeline.fit(X_train, y_train)
    print("✅  Training complete!")

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n📈  Test Accuracy: {acc*100:.1f}%")
    print("\n" + classification_report(y_test, y_pred))

    joblib.dump(pipeline, "sentiment_model.pkl")
    print("💾  Model saved → sentiment_model.pkl")

    labels = ["negative", "positive"]
    cm = confusion_matrix(y_test, y_pred, labels=labels)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f0f1a")

    ax1 = axes[0]
    sns.heatmap(cm, annot=True, fmt="d", cmap="RdPu",
        xticklabels=labels, yticklabels=labels,
        ax=ax1, linewidths=0.5, linecolor="#1a1a2e",
        annot_kws={"size": 14, "weight": "bold"})
    ax1.set_title("Confusion Matrix", color="white", fontsize=14, pad=12)
    ax1.set_xlabel("Predicted", color="#c084fc")
    ax1.set_ylabel("Actual", color="#c084fc")
    ax1.tick_params(colors="white")
    ax1.set_facecolor("#0f0f1a")

    ax2 = axes[1]
    counts = df["label"].value_counts()
    bars = ax2.bar(counts.index, counts.values,
                   color=["#f87171", "#4ade80"], width=0.5, edgecolor="#1a1a2e")
    for bar, val in zip(bars, counts.values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
                 f"{val:,}", ha="center", va="bottom",
                 color="white", fontsize=12, fontweight="bold")
    ax2.set_title("Training Data", color="white", fontsize=14, pad=12)
    ax2.set_ylabel("Tweets", color="#c084fc")
    ax2.tick_params(colors="white")
    ax2.set_facecolor("#0f0f1a")
    for spine in ax2.spines.values():
        spine.set_visible(False)

    plt.suptitle(f"Kaggle Sentiment Model — Accuracy: {acc*100:.1f}%",
                 color="white", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig("training_results.png", dpi=150, bbox_inches="tight", facecolor="#0f0f1a")
    print("📊  Chart saved → training_results.png")
    print(f"\n🎉  Done! Accuracy: {acc*100:.1f}%")
    print("    Now run:  python predict.py\n")

if __name__ == "__main__":
    train()