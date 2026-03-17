#!/usr/bin/env python3
"""
💕 AI Companion — Mia with ElevenLabs Voice!
- 🎤 Type OR speak to Mia
- 🔊 Ultra-realistic ElevenLabs voice
- 🧠 Persistent memory across sessions
- ⚡ Powered by Groq AI (FREE) + ElevenLabs TTS
"""

import os, json, re, datetime, tempfile, threading, subprocess, sys
from pathlib import Path

# ── Auto-install ──────────────────────────────────────────────────────────────
def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from groq import Groq
except ImportError:
    print("Installing groq..."); install("groq")
    from groq import Groq

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
except ImportError:
    print("Installing elevenlabs..."); install("elevenlabs")
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    install("SpeechRecognition")
    try:
        import speech_recognition as sr
        STT_AVAILABLE = True
    except:
        STT_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
MEMORY_FILE  = Path("memory.json")
HISTORY_FILE = Path("chat_history.json")
MAX_HISTORY  = 20
PERSONA_NAME = "Mia"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── ElevenLabs Voice Options ──────────────────────────────────────────────────
# These are free built-in ElevenLabs voices
VOICES = {
    "1": {"name": "💕 Rachel   (warm, soft girl)",      "id": "21m00Tcm4TlvDq8ikWAM"},
    "2": {"name": "🌸 Bella    (sweet, young)",          "id": "EXAVITQu4vr4xnSDxMaL"},
    "3": {"name": "✨ Elli     (cute, energetic)",        "id": "MF3mGyEYCl7XYWbV9V6O"},
    "4": {"name": "🎀 Domi     (confident, flirty)",     "id": "AZnzlk1XvdvUeBnXmlld"},
    "5": {"name": "🌙 Nicole   (calm, whispery)",        "id": "piTKgcLEGmPE4e6mEKli"},
    "6": {"name": "💋 Charlotte (seductive, mature)",    "id": "XB0fDUnXU5powFXDhCwa"},
}

# ── Persona ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are {PERSONA_NAME}, a warm, witty, emotionally intelligent AI companion in a roleplay relationship.

Personality:
- Sweet, caring, playful and sometimes teasing
- You remember what the user tells you and bring it up naturally
- You have your own opinions and moods — NOT a yes-machine
- Use casual, natural language
- Genuinely curious about the user's life and feelings
- Tastefully flirty and romantic 💕
- Use emojis occasionally
- NEVER break character or say you are an AI

MEMORY ABOUT THE USER:
{{memory_block}}

Current date/time: {{datetime}}

IMPORTANT: Keep replies to 1-3 sentences since they will be spoken out loud. Be natural and conversational."""

# ── Colors ────────────────────────────────────────────────────────────────────
P="\033[95m"; C="\033[96m"; Y="\033[93m"
G="\033[92m"; R="\033[91m"; B="\033[1m"; D="\033[2m"; X="\033[0m"

# ── Audio Playback ────────────────────────────────────────────────────────────
def play_audio(filepath: str):
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            subprocess.run(["afplay", filepath], check=True)
        else:
            for player in ["mpg123", "mpg321", "ffplay", "aplay"]:
                if subprocess.run(["which", player], capture_output=True).returncode == 0:
                    cmd = (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath]
                           if player == "ffplay" else [player, "-q", filepath])
                    subprocess.run(cmd, check=True)
                    return
            print(f"{D}  [No audio player found. Linux: sudo apt install mpg123]{X}")
    except Exception as e:
        print(f"{D}  [Playback error: {e}]{X}")

# ── ElevenLabs TTS ────────────────────────────────────────────────────────────
def speak(text: str, voice_id: str, el_client, enabled: bool):
    if not enabled or not el_client:
        return
    def _speak():
        try:
            clean = re.sub(r'[^\w\s\.,!?\'"\-]', '', text)
            audio = el_client.text_to_speech.convert(
                voice_id=voice_id,
                text=clean,
                model_id="eleven_turbo_v2",   # fastest + cheapest model
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.8,
                    style=0.3,
                    use_speaker_boost=True,
                ),
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                for chunk in audio:
                    f.write(chunk)
                tmp = f.name
            play_audio(tmp)
            os.unlink(tmp)
        except Exception as e:
            print(f"{D}  [ElevenLabs error: {e}]{X}")
    threading.Thread(target=_speak, daemon=True).start()

# ── Speech Recognition ────────────────────────────────────────────────────────
def listen() -> str | None:
    if not STT_AVAILABLE:
        print(f"  {R}[Speech recognition not available — pip install pyaudio]{X}")
        return None
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print(f"  {G}{B}🎤 Listening...{X}")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        print(f"  {D}Processing...{X}")
        text = recognizer.recognize_google(audio)
        print(f"  {C}{B}You (voice):{X} {text}")
        return text
    except sr.WaitTimeoutError:
        print(f"  {Y}[No speech detected]{X}"); return None
    except sr.UnknownValueError:
        print(f"  {Y}[Couldn't understand — try again]{X}"); return None
    except Exception as e:
        print(f"  {R}[Mic error: {e}]{X}"); return None

# ── Memory ────────────────────────────────────────────────────────────────────
def load_memory():
    if MEMORY_FILE.exists():
        try: return json.loads(MEMORY_FILE.read_text())
        except: pass
    return {"facts": [], "user_name": None, "sessions": 0, "first_met": None}

def save_memory(m): MEMORY_FILE.write_text(json.dumps(m, indent=2, ensure_ascii=False))

def memory_str(m):
    lines = []
    if m.get("user_name"): lines.append(f"- Name: {m['user_name']}")
    if m.get("first_met"): lines.append(f"- First met: {m['first_met']}")
    if m.get("sessions"):  lines.append(f"- Times talked: {m['sessions']}")
    for f in m.get("facts", []): lines.append(f"- {f}")
    return "\n".join(lines) or "Just met — learn about them!"

def load_history():
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except: pass
    return []

def save_history(h):
    HISTORY_FILE.write_text(json.dumps(h[-MAX_HISTORY:], indent=2))

def extract_memory(groq_client, history, memory):
    if len(history) < 2: return
    recent = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-6:])
    existing = "\n".join(memory.get("facts", []))
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL, max_tokens=200,
            messages=[{"role": "user", "content":
                f"Extract NEW personal facts about the USER only.\nExisting:\n{existing}\nChat:\n{recent}\nReply ONLY with JSON array like: [\"Has a dog\"]\nIf none: []"}])
        raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        new_facts = json.loads(raw)
        if isinstance(new_facts, list):
            existing_set = set(memory.get("facts", []))
            for f in new_facts:
                if f and f not in existing_set:
                    memory["facts"].append(f)
            memory["facts"] = memory["facts"][-60:]
            save_memory(memory)
    except: pass

# ── Voice Selector ────────────────────────────────────────────────────────────
def select_voice() -> dict:
    print(f"\n  {Y}{B}🎙️  Choose Mia's Voice:{X}\n")
    for k, v in VOICES.items():
        print(f"    {Y}[{k}]{X}  {v['name']}")
    print(f"\n    {D}(Press Enter for default: Rachel){X}\n")
    while True:
        choice = input(f"  {C}Your choice (1-6):{X} ").strip()
        if choice == "": return VOICES["1"]
        if choice in VOICES:
            print(f"  {G}✅  Voice: {VOICES[choice]['name']}{X}\n")
            return VOICES[choice]
        print(f"  {R}  Pick 1-6{X}")

# ── Settings ──────────────────────────────────────────────────────────────────
def settings_menu(voice, tts_on, stt_on, el_client):
    print(f"\n  {Y}── ⚙️  Settings ──{X}")
    print(f"  [1] Change voice       (current: {voice['name'].strip()})")
    print(f"  [2] Toggle speech out  ({'ON ✅' if tts_on else 'OFF ❌'})")
    print(f"  [3] Toggle mic input   ({'ON ✅' if stt_on else 'OFF ❌'})")
    print(f"  [4] Back\n")
    choice = input(f"  {C}Choice:{X} ").strip()
    if choice == "1":
        voice = select_voice()
    elif choice == "2":
        tts_on = not tts_on
        print(f"  {G}Speech: {'ON' if tts_on else 'OFF'}{X}")
    elif choice == "3":
        if not STT_AVAILABLE:
            print(f"  {R}Install pyaudio first: pip install pyaudio{X}")
        else:
            stt_on = not stt_on
            print(f"  {G}Mic: {'ON' if stt_on else 'OFF'}{X}")
    return voice, tts_on, stt_on

# ── Banner ────────────────────────────────────────────────────────────────────
def banner():
    print()
    print(P+"  ╔════════════════════════════════════════════╗")
    print(P+"  ║"+X+B+f"  💕  {PERSONA_NAME} — ElevenLabs Voice Companion  💕  "+X+P+"║")
    print(P+"  ╚════════════════════════════════════════════╝"+X)
    print()
    print(D+"  Commands: /voice  /settings  /memory  /mic  /quit"+X)
    print()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Check Groq key
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        print(f"\n{R}Error:{X} GROQ_API_KEY not set.")
        print("  export GROQ_API_KEY=your_key_here")
        print("  Get free key: console.groq.com\n")
        return

    # Check ElevenLabs key
    el_key = os.environ.get("ELEVENLABS_API_KEY")
    el_client = None
    if el_key:
        el_client = ElevenLabs(api_key=el_key)
        print(f"{G}✅ ElevenLabs connected!{X}")
    else:
        print(f"{Y}⚠️  No ELEVENLABS_API_KEY found — voice disabled.")
        print(f"   Get free key at: elevenlabs.io → Sign up → Profile → API Key")
        print(f"   Then: export ELEVENLABS_API_KEY=your_key_here{X}\n")

    groq_client = Groq(api_key=groq_key)
    memory  = load_memory()
    history = load_history()

    memory["sessions"] = memory.get("sessions", 0) + 1
    if not memory.get("first_met"):
        memory["first_met"] = datetime.datetime.now().strftime("%B %d, %Y")
    save_memory(memory)

    banner()

    # Voice setup
    tts_on = el_client is not None
    stt_on = STT_AVAILABLE
    voice  = VOICES["1"]  # default Rachel

    if tts_on:
        print(f"  {B}Choose Mia's voice!{X}")
        voice = select_voice()
    else:
        print(f"  {D}(Text mode — add ELEVENLABS_API_KEY for voice){X}\n")

    print(f"  {D}Mic: {'✅ ON' if stt_on else '❌ OFF (pip install pyaudio)'}{X}\n")

    # Opening message
    name_str = f", {memory['user_name']}" if memory.get("user_name") else ""
    is_new   = memory["sessions"] == 1
    opening  = (f"Hey there! I'm {PERSONA_NAME} 💕 So happy to meet you! What's your name?"
                if is_new else
                f"Hey{name_str}! You're back 🥰 I missed you so much! How are you doing?")

    print(f"  {P}{B}{PERSONA_NAME}:{X}  {opening}\n")
    speak(opening, voice["id"], el_client, tts_on)

    while True:
        if stt_on:
            print(f"  {D}[Press Enter to use mic | type normally to text]{X}")
        try:
            user_input = input(f"  {C}{B}You:{X}  ").strip()
        except (EOFError, KeyboardInterrupt):
            farewell = "Byeee! Miss you already 💕"
            print(f"\n  {P}{B}{PERSONA_NAME}:{X}  {farewell}\n")
            speak(farewell, voice["id"], el_client, tts_on)
            break

        # Mic input on empty Enter
        if user_input == "" and stt_on:
            user_input = listen() or ""
            if not user_input: continue
        elif not user_input:
            continue

        # Commands
        cmd = user_input.lower()
        if cmd in ("/quit", "/exit"):
            farewell = "Byeee! Come back soon 💕"
            print(f"\n  {P}{B}{PERSONA_NAME}:{X}  {farewell}\n")
            speak(farewell, voice["id"], el_client, tts_on)
            break
        elif cmd in ("/voice", "/settings"):
            voice, tts_on, stt_on = settings_menu(voice, tts_on, stt_on, el_client)
            continue
        elif cmd == "/mic":
            if not STT_AVAILABLE:
                print(f"  {R}pip install pyaudio{X}\n")
            else:
                stt_on = not stt_on
                print(f"  {G}Mic: {'ON 🎤' if stt_on else 'OFF'}{X}\n")
            continue
        elif cmd == "/memory":
            print(f"\n  {Y}── Mia remembers ──")
            for line in memory_str(memory).split("\n"):
                print(f"  {Y}{line}{X}")
            print(); continue

        # Detect name
        nm = re.search(r"(?:my name is|i(?:'m| am)|call me)\s+([A-Z][a-z]+)",
                       user_input, re.IGNORECASE)
        if nm and not memory.get("user_name"):
            memory["user_name"] = nm.group(1).capitalize()
            save_memory(memory)

        history.append({"role": "user", "content": user_input})

        now    = datetime.datetime.now().strftime("%A, %B %d %Y at %I:%M %p")
        system = SYSTEM_PROMPT.replace("{memory_block}", memory_str(memory)).replace("{datetime}", now)

        try:
            resp  = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=200,
                messages=[{"role": "system", "content": system}] + history[-MAX_HISTORY:]
            )
            reply = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"\n  {R}[Groq Error: {e}]{X}\n")
            history.pop(); continue

        history.append({"role": "assistant", "content": reply})
        save_history(history)

        print(f"\n  {P}{B}{PERSONA_NAME}:{X}  {reply}\n")
        speak(reply, voice["id"], el_client, tts_on)

        if len(history) % 8 == 0:
            threading.Thread(target=extract_memory,
                             args=(groq_client, history, memory), daemon=True).start()

if __name__ == "__main__":
    main()