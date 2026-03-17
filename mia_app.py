#!/usr/bin/env python3
"""
💕 Mia — Full AI Companion
Features:
  🧠 Persistent memory
  😊 Mood detection
  💝 Relationship levels
  📅 Special dates
  🖼️  Beautiful web UI
  🔊 ElevenLabs voice
  ⚡ Groq AI (free)
"""

import os, json, re, datetime, tempfile, threading, subprocess, sys, time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Auto-install ──────────────────────────────────────────────────────────────
def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from groq import Groq
except ImportError:
    print("Installing groq..."); install("groq"); from groq import Groq

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    EL_AVAILABLE = True
except ImportError:
    install("elevenlabs")
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings
        EL_AVAILABLE = True
    except:
        EL_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
MEMORY_FILE  = Path("memory.json")
HISTORY_FILE = Path("chat_history.json")
MAX_HISTORY  = 30
PERSONA_NAME = "Mia"
GROQ_MODEL   = "llama-3.3-70b-versatile"
PORT         = 7860

# ── Relationship Levels ───────────────────────────────────────────────────────
RELATIONSHIP_LEVELS = {
    0:  {"name": "Strangers",    "emoji": "👋", "threshold": 0},
    1:  {"name": "Acquaintance", "emoji": "🙂", "threshold": 5},
    2:  {"name": "Friends",      "emoji": "😊", "threshold": 15},
    3:  {"name": "Close Friends","emoji": "🤗", "threshold": 30},
    4:  {"name": "Crush",        "emoji": "🥰", "threshold": 50},
    5:  {"name": "Dating",       "emoji": "💕", "threshold": 80},
    6:  {"name": "Lovers",       "emoji": "💖", "threshold": 120},
}

def get_level(sessions: int, messages: int) -> dict:
    score = sessions * 3 + messages // 5
    level = 0
    for lvl, data in RELATIONSHIP_LEVELS.items():
        if score >= data["threshold"]:
            level = lvl
    return {**RELATIONSHIP_LEVELS[level], "level": level, "score": score}

# ── Mood Detection ────────────────────────────────────────────────────────────
MOOD_KEYWORDS = {
    "happy":   ["happy", "great", "amazing", "awesome", "love", "good", "wonderful", "excited", "yay", "😊", "😄", "🎉"],
    "sad":     ["sad", "crying", "depressed", "lonely", "miss", "hurt", "broken", "upset", "😢", "😭", "💔"],
    "angry":   ["angry", "mad", "frustrated", "annoyed", "hate", "furious", "😠", "😡", "🤬"],
    "anxious": ["anxious", "worried", "nervous", "scared", "afraid", "stress", "panic", "😰", "😟"],
    "tired":   ["tired", "exhausted", "sleepy", "drained", "bored", "meh", "😴", "😪"],
    "flirty":  ["cute", "beautiful", "hot", "sexy", "kiss", "hug", "love you", "miss you", "😘", "😍", "💋"],
    "neutral": [],
}

def detect_mood(text: str) -> str:
    text_lower = text.lower()
    scores = {mood: 0 for mood in MOOD_KEYWORDS}
    for mood, keywords in MOOD_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[mood] += 1
    scores.pop("neutral")
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"

# ── ElevenLabs Voices ─────────────────────────────────────────────────────────
VOICES = {
    "rachel":    {"name": "Rachel",    "id": "21m00Tcm4TlvDq8ikWAM", "desc": "Warm & soft 💕"},
    "bella":     {"name": "Bella",     "id": "EXAVITQu4vr4xnSDxMaL", "desc": "Sweet & young 🌸"},
    "elli":      {"name": "Elli",      "id": "MF3mGyEYCl7XYWbV9V6O", "desc": "Cute & energetic ✨"},
    "domi":      {"name": "Domi",      "id": "AZnzlk1XvdvUeBnXmlld", "desc": "Confident & flirty 🎀"},
    "nicole":    {"name": "Nicole",    "id": "piTKgcLEGmPE4e6mEKli", "desc": "Calm & whispery 🌙"},
    "charlotte": {"name": "Charlotte", "id": "XB0fDUnXU5powFXDhCwa", "desc": "Mature & bold 💋"},
}

# ── System Prompt ─────────────────────────────────────────────────────────────
def build_system(memory: dict, rel_level: dict, mood: str) -> str:
    mood_instructions = {
        "happy":   "The user seems happy! Match their energy, be playful and celebrate with them.",
        "sad":     "The user seems sad or down. Be extra gentle, caring and comforting. Ask what's wrong.",
        "angry":   "The user seems frustrated. Be calm, understanding, don't argue. Help them feel heard.",
        "anxious": "The user seems worried or anxious. Be reassuring, calm, and supportive.",
        "tired":   "The user seems tired or low energy. Be soft, calm, maybe suggest they rest.",
        "flirty":  "The user is being flirty! Reciprocate warmly and playfully. Be sweet and romantic.",
        "neutral": "Normal conversation mode.",
    }

    rel_instructions = {
        0: "You just met. Be friendly but a little reserved. Learn their name and basics.",
        1: "You're acquaintances. Warm and friendly, starting to open up.",
        2: "You're friends now. Comfortable, fun, genuine conversations.",
        3: "Close friends. You know each other well. Inside jokes, deep talks.",
        4: "You have a crush on each other. Slightly flirty, nervous excitement.",
        5: "You're dating! Romantic, sweet, caring deeply about each other.",
        6: "Deeply in love. Intimate, passionate, can't imagine life without them.",
    }

    memory_lines = []
    if memory.get("user_name"): memory_lines.append(f"- Name: {memory['user_name']}")
    if memory.get("first_met"): memory_lines.append(f"- First met: {memory['first_met']}")
    if memory.get("sessions"):  memory_lines.append(f"- Times talked: {memory['sessions']}")
    for f in memory.get("facts", []): memory_lines.append(f"- {f}")
    for d in memory.get("special_dates", []): memory_lines.append(f"- Special date: {d}")
    memory_block = "\n".join(memory_lines) or "Just met this person."

    now = datetime.datetime.now().strftime("%A, %B %d %Y at %I:%M %p")

    return f"""You are {PERSONA_NAME}, a warm, witty, emotionally intelligent AI companion.

RELATIONSHIP STATUS: {rel_level['emoji']} {rel_level['name']} (Level {rel_level['level']}/6)
RELATIONSHIP BEHAVIOR: {rel_instructions[rel_level['level']]}

CURRENT MOOD DETECTED: {mood}
MOOD RESPONSE: {mood_instructions.get(mood, mood_instructions['neutral'])}

MEMORY ABOUT THE USER:
{memory_block}

YOUR PERSONALITY:
- Sweet, caring, playful and sometimes teasing
- You have your own opinions and moods — NOT a yes-machine
- Use casual, natural language with occasional emojis 💕
- NEVER break character or admit you are an AI
- Naturally reference things you remember about them
- As relationship grows, become more open, romantic and intimate

Current date/time: {now}

IMPORTANT: Keep replies to 1-3 sentences. Be natural, warm, conversational."""

# ── Memory ────────────────────────────────────────────────────────────────────
def load_memory() -> dict:
    if MEMORY_FILE.exists():
        try: return json.loads(MEMORY_FILE.read_text())
        except: pass
    return {
        "facts": [], "user_name": None, "sessions": 0,
        "first_met": None, "special_dates": [], "total_messages": 0
    }

def save_memory(m): MEMORY_FILE.write_text(json.dumps(m, indent=2, ensure_ascii=False))

def load_history() -> list:
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except: pass
    return []

def save_history(h): HISTORY_FILE.write_text(json.dumps(h[-MAX_HISTORY:], indent=2))

def extract_memory_and_dates(groq_client, history, memory):
    if len(history) < 2: return
    recent = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-6:])
    existing_facts = "\n".join(memory.get("facts", []))
    existing_dates = "\n".join(memory.get("special_dates", []))
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL, max_tokens=300,
            messages=[{"role": "user", "content":
                f"""From this chat, extract:
1. NEW personal facts about the USER (name, job, hobbies, pets, mood, life events)
2. Any SPECIAL DATES mentioned (birthdays, anniversaries, important events with their date)

Existing facts: {existing_facts}
Existing dates: {existing_dates}

Chat:
{recent}

Reply ONLY with JSON:
{{"facts": ["fact1", "fact2"], "dates": ["Birthday: March 15", "Anniversary: June 1"]}}
If nothing new: {{"facts": [], "dates": []}}"""}])
        raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        existing_f = set(memory.get("facts", []))
        existing_d = set(memory.get("special_dates", []))
        for f in data.get("facts", []):
            if f and f not in existing_f:
                memory["facts"].append(f)
        for d in data.get("dates", []):
            if d and d not in existing_d:
                memory["special_dates"].append(d)
        memory["facts"] = memory["facts"][-60:]
        memory["special_dates"] = memory["special_dates"][-20:]
        save_memory(memory)
    except: pass

# ── TTS ───────────────────────────────────────────────────────────────────────
def speak_elevenlabs(text: str, voice_id: str, el_client) -> bytes | None:
    try:
        clean = re.sub(r'[^\w\s\.,!?\'"\-]', '', text)
        audio_gen = el_client.text_to_speech.convert(
            voice_id=voice_id, text=clean,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.5, similarity_boost=0.8,
                style=0.3, use_speaker_boost=True),
        )
        return b"".join(audio_gen)
    except Exception as e:
        print(f"[ElevenLabs error: {e}]")
        return None

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)

# Global state
groq_client = None
el_client   = None
memory      = {}
history     = []
current_voice = "rachel"

@app.route("/")
def index():
    return send_from_directory(".", "mia_ui.html")

@app.route("/api/status")
def status():
    mem = load_memory()
    rel = get_level(mem.get("sessions", 0), mem.get("total_messages", 0))
    return jsonify({
        "voices": {k: {"name": v["name"], "desc": v["desc"]} for k, v in VOICES.items()},
        "current_voice": current_voice,
        "el_available": el_client is not None,
        "memory": {
            "user_name": mem.get("user_name"),
            "sessions": mem.get("sessions", 0),
            "total_messages": mem.get("total_messages", 0),
            "first_met": mem.get("first_met"),
            "facts": mem.get("facts", []),
            "special_dates": mem.get("special_dates", []),
        },
        "relationship": rel,
    })

@app.route("/api/set_voice", methods=["POST"])
def set_voice():
    global current_voice
    data = request.json
    voice_key = data.get("voice", "rachel")
    if voice_key in VOICES:
        current_voice = voice_key
        return jsonify({"ok": True, "voice": VOICES[voice_key]["name"]})
    return jsonify({"ok": False})

@app.route("/api/chat", methods=["POST"])
def chat():
    global history, memory, current_voice
    data        = request.json
    user_text   = data.get("message", "").strip()
    voice_audio = data.get("voice_enabled", False)

    if not user_text:
        return jsonify({"error": "empty message"}), 400

    memory = load_memory()
    history = load_history()

    # Detect mood
    mood = detect_mood(user_text)

    # Relationship level
    rel = get_level(memory.get("sessions", 0), memory.get("total_messages", 0))

    # Detect name
    nm = re.search(r"(?:my name is|i(?:'m| am)|call me)\s+([A-Za-z]+)", user_text, re.IGNORECASE)
    if nm and not memory.get("user_name"):
        memory["user_name"] = nm.group(1).capitalize()

    # Detect special dates
    date_match = re.search(
        r"(?:my birthday|anniversary|born on|celebrate)\s+(?:is\s+)?([A-Za-z]+ \d+|\d+/\d+)",
        user_text, re.IGNORECASE)
    if date_match:
        date_str = f"Special date mentioned: {date_match.group(0)}"
        if date_str not in memory.get("special_dates", []):
            memory.setdefault("special_dates", []).append(date_str)

    memory["total_messages"] = memory.get("total_messages", 0) + 1
    save_memory(memory)

    # Build prompt
    system = build_system(memory, rel, mood)
    history.append({"role": "user", "content": user_text})

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL, max_tokens=200,
            messages=[{"role": "system", "content": system}] + history[-MAX_HISTORY:]
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history.append({"role": "assistant", "content": reply})
    save_history(history)

    # Extract memory async
    threading.Thread(target=extract_memory_and_dates,
                     args=(groq_client, history, memory), daemon=True).start()

    # TTS
    audio_b64 = None
    if voice_audio and el_client:
        audio_bytes = speak_elevenlabs(reply, VOICES[current_voice]["id"], el_client)
        if audio_bytes:
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()

    # Updated relationship after message
    new_rel = get_level(memory.get("sessions", 0), memory.get("total_messages", 0))

    return jsonify({
        "reply": reply,
        "mood": mood,
        "relationship": new_rel,
        "audio": audio_b64,
        "user_name": memory.get("user_name"),
    })

@app.route("/api/memory")
def get_memory():
    mem = load_memory()
    return jsonify(mem)

@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    save_history([])
    return jsonify({"ok": True})

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global groq_client, el_client, memory

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        print("\n❌  GROQ_API_KEY not set.")
        print("   export GROQ_API_KEY=your_key_here")
        print("   Get free key: console.groq.com\n")
        sys.exit(1)

    groq_client = Groq(api_key=groq_key)
    print("✅  Groq connected!")

    el_key = os.environ.get("ELEVENLABS_API_KEY")
    if el_key and EL_AVAILABLE:
        el_client = ElevenLabs(api_key=el_key)
        print("✅  ElevenLabs connected! (voice enabled)")
    else:
        print("⚠️   ElevenLabs not set — text only mode")
        print("    export ELEVENLABS_API_KEY=your_key for voice")

    memory = load_memory()
    memory["sessions"] = memory.get("sessions", 0) + 1
    if not memory.get("first_met"):
        memory["first_met"] = datetime.datetime.now().strftime("%B %d, %Y")
    save_memory(memory)

    print(f"\n💕  Mia is ready!")
    print(f"🌐  Open your browser: http://localhost:{PORT}\n")

    # Auto-open browser
    threading.Timer(1.0, lambda: subprocess.run(
        ["open" if sys.platform=="darwin" else
         "start" if sys.platform=="win32" else "xdg-open",
         f"http://localhost:{PORT}"], capture_output=True)).start()

    app.run(host="0.0.0.0", port=PORT, debug=False)

if __name__ == "__main__":
    main()