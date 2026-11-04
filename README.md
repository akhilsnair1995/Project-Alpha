# Project Alpha: Wall-E Autonomous Companion Rover

Project Alpha is a physical desktop robot companion inspired by Wall-E. It features an acrylic tracked crawler chassis, a 2-axis pan/tilt binocular head with dual round LCD eyes, center-bridge computer vision, onboard SQLite spatial memory, 4G cellular & WiFi failover, and a hybrid AI brain powered by Google Gemini 2.5 with offline Gemma fallback.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │             PROJECT ALPHA               │
                      └────────────────────┬────────────────────┘
                                           │
         ┌──────────────────┬──────────────┼──────────────────┬──────────────────┐
         ▼                  ▼              ▼                  ▼                  ▼
  [Vision Cortex]   [Dual-Eye Engine] [Voice Cortex]   [Knowledge Graph]  [Motion & Kinematics]
  • OpenCV Face     • 2x 1.28" GC9A01 • Wall-E Chirps  • SQLite Onboard   • Pan/Tilt Servos
  • ArUco Docking   • 16 Expressions  • SAPI5/TTS      • User Fact Memory • Crawler Tracks
  • Scene Novelty   • Blink & Winks   • Soundboard     • Episodic Logs    • Table Cliff IR
         │                  │              │                  │                  │
         └──────────────────┴──────────────┼──────────────────┴──────────────────┘
                                           ▼
                             ┌───────────────────────────┐
                             │     HYBRID BRAIN CORE     │
                             │  Online: Gemini 2.5 Flash │
                             │  Offline: Local Gemma GGUF│
                             └───────────────────────────┘
```

---

## Project Structure

```
├── core/
│   ├── config.py              # Pin assignments, thresholds, and paths
│   ├── database.py            # SQLite knowledge graph & user memory manager
│   ├── eye_animator.py        # Dual 1.28" LCD (GC9A01) procedural 16-expression engine
│   ├── voice_engine.py        # Procedural Wall-E sound synthesizer & cross-platform TTS
│   ├── gemini_brain.py        # Gemini 2.5 multimodal agent with emotional expression parsing
│   ├── motion_controller.py   # MG90S neck servos, DRV8833 tracks & emotional body gestures
│   └── vision_pipeline.py     # Face detection, ArUco dock homing & scene analysis
├── hardware/
│   ├── BOM.md                 # Complete Bill of Materials
│   ├── BUYING_GUIDE_INDIA.md  # Verified procurement links for Kerala / India
│   ├── CHARGING_DOCK_SPEC.md  # Autonomous docking & underside contactor design
│   ├── CHASSIS_SPECS.md       # 100% pre-cut acrylic plate specifications
│   └── laser_cut/
│       ├── walle_chassis_complete_cutsheet.svg  # 1:1 scale laser cut blueprint (15 plates)
│       └── walle_charging_dock_cutsheet.svg     # 1:1 scale dock laser cut blueprint
├── simulator/
│   ├── index.html             # Interactive Digital Twin browser simulator
│   └── run_sim.py             # Python HTTP server launcher with REST & audio streaming
├── tests/
│   ├── test_database.py       # Unit tests for SQLite memory engine
│   ├── test_learning.py       # Unit tests for continuous fact & spatial learning
│   ├── test_expressions.py    # Unit tests for 16 eye expressions & gaze clamping
│   └── test_voice.py          # Unit tests for procedural sound synthesis & TTS
├── data/snapshots/            # Exported renders of all 16 eye emotional states
├── main.py                    # Main daemon entrypoint (CLI chat & autonomous loop)
└── requirements.txt           # Python dependencies
```

---

## Quick Start (PC Development & Testing)

The entire software stack features automatic hardware simulation fallbacks so you can develop, chat, and test on your PC before deploying to the Raspberry Pi:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Export & Preview Dual-Eye Expressions
Generate PNG renders of the dual eyes across all 16 emotional states (`idle`, `happy`, `curious`, `squint`, `wink`, `sad`, `sleepy`, `surprised`, `alert`, `analyzing`, `excited`, `love`, `angry`, `confused`, `skeptical`, `offline`):
```bash
python main.py --preview-eyes
```
Renders are saved in `data/snapshots/`.

### 3. Interactive Chat with Voice & Continuous Memory
Chat with Alpha in terminal to test its voice synthesis, emotional expressions, memory, and personality:
```bash
python main.py --cli --voice
```
* Type `facts` to see what Alpha currently remembers about you in SQLite.
* Type `history` to view recent conversational turns.
* Type `eyes excited` or `eyes love` to switch expressions and trigger expressive head gestures.
* Type `sound happy`, `sound alert`, or `sound startup` to play procedural Wall-E chimes.
* Type `voice on` / `voice off` to toggle spoken speech.

### 4. Run the Digital Twin & Cognitive Web Simulator
Launch the full digital twin featuring tabletop kinematics, live SQLite memory tables, laptop camera face tracking, procedural Wall-E audio synthesizer, and multimodal Gemini vision:
```bash
python simulator/run_sim.py
```
Open `http://localhost:8085` in your browser. Key capabilities included:
* **Tabletop Roam Arena**: Tank drive kinematics, TCRT5000 cliff edge protection, ToF laser raycasting, and draggable objects (`CUBE`, `CUP`, `KEYS`, `BOOK`) with automatic proximity sighting into SQLite.
* **Dual GC9A01 LCD Screens (16 Expressions)**: Expressive procedural eyes reflecting 16 emotional states, interactive 2D gaze trackpad, and auto-blink.
* **Wall-E Sound Synthesizer & Soundboard**: 12 procedural sound trigger buttons (`Startup`, `Happy`, `Curious`, `Excited`, `Alert`, `Love`, `Sad`, `Bump`, `Wink`, `Confused`, `Angry`, `Power Down`) powered by Web Audio API and Python backend WAV generation.
* **Live Speech & Voice Cortex**: Chat with Alpha via text or microphone (Web Speech API). Features Wall-E voice pitch modulation (1.35x), speed control, real-time dynamic audio spectrum visualizer, and talking eye pupil pulsing.
* **Wired Simulation Reactions**: Table cliff edge triggers alert siren and recoil; obstacle bump triggers impact squeak; proximity triggers curious chirps; head petting triggers purrs and loving tilts!
* **AI Brain & SQLite Memory Inspector**: Real-time dashboard of persistent SQLite tables (`UserFacts`, `DiscoveredObjects` with moved tracking, `RoamingObservations`, and `ChatHistory`) with live cloud/offline toggle.

### 5. Run Unit Tests
```bash
python -m unittest discover tests/
```
