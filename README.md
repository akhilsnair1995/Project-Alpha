# Project Alpha: Wall-E Autonomous Companion Rover

Project Alpha is a physical desktop robot companion inspired by Wall-E. It features an acrylic tracked crawler chassis, a 2-axis pan/tilt binocular head with dual round LCD eyes, center-bridge computer vision, onboard SQLite spatial memory, 4G cellular & WiFi failover, and a hybrid AI brain powered by Google Gemini 2.5 with offline Gemma fallback.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │             PROJECT ALPHA               │
                      └────────────────────┬────────────────────┘
                                           │
         ┌──────────────────┬──────────────┴─────┬──────────────────┐
         ▼                  ▼                    ▼                  ▼
  [Vision Cortex]   [Dual-Eye Engine]    [Knowledge Graph]   [Motion & Kinematics]
  • OpenCV Face     • 2x 1.28" GC9A01    • SQLite Onboard    • Pan/Tilt Servos
  • ArUco Docking   • Expressive Pupils  • User Fact Memory  • Crawler Tracks
  • Scene Novelty   • Blink & Winks      • Episodic Logs     • Table Cliff IR
         │                  │                    │                  │
         └──────────────────┼────────────────────┴──────────────────┘
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
│   ├── eye_animator.py        # Dual 1.28" LCD (GC9A01) procedural animation engine
│   ├── gemini_brain.py        # Gemini 2.5 multimodal agent with memory extraction
│   ├── motion_controller.py   # MG90S neck servos & DRV8833 crawler track driver
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
│   └── run_sim.py             # Python HTTP server launcher for simulator
├── tests/
│   └── test_database.py       # Unit tests for SQLite memory engine
├── data/snapshots/            # Exported renders of eye emotional states
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
Generate PNG renders of the dual eyes across all 9 emotional states (`happy`, `curious`, `wink`, `sleepy`, `skeptical`, `surprised`, `analyzing`, `offline`):
```bash
python main.py --preview-eyes
```
Renders are saved in `data/snapshots/`.

### 3. Interactive Chat & Continuous Memory Test
Chat with Alpha in terminal to test its memory, fact-learning engine, and personality:
```bash
python main.py --cli
```
* Type `facts` to see what Alpha currently remembers about you in SQLite.
* Type `history` to view recent conversational turns.
* Type `eyes curious` or `eyes wink` to switch expressions.

### 4. Run the Digital Twin & Cognitive Web Simulator
Launch the full digital twin featuring tabletop kinematics, live SQLite memory tables, laptop camera face tracking, and multimodal Gemini vision:
```bash
python simulator/run_sim.py
```
Open `http://localhost:8085` in your browser. Key capabilities included:
* **Tabletop Roam Arena**: Tank drive kinematics, TCRT5000 cliff edge protection, ToF laser raycasting, and draggable objects (`CUBE`, `CUP`, `KEYS`, `BOOK`) with automatic proximity sighting into SQLite.
* **Dual GC9A01 LCD Screens**: Expressive procedural eyes reflecting 9 emotional states and live eyelid kinematics.
* **Laptop Webcam (Alpha Eye)**: Uses your laptop's camera to emulate Alpha's nose-bridge camera. Tracks your face in real-time to steer the neck pan/tilt servos and gaze, and provides a **"Show & Tell (Gemini Vision)"** button to inspect objects in front of you.
* **Live Speech & Voice Cortex**: Chat with Alpha via text or microphone (Web Speech API). Features Wall-E voice TTS playback and automatic personal fact extraction.
* **AI Brain & SQLite Memory Inspector**: Real-time dashboard of persistent SQLite tables (`UserFacts`, `DiscoveredObjects` with moved tracking, `RoamingObservations`, and `ChatHistory`) with live cloud/offline toggle.

### 5. Run Unit Tests
```bash
python -m unittest discover tests/
```
