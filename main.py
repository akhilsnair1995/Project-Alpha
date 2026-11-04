"""
Project Alpha: Main Entrypoint & Autonomous Robot Daemon.
Coordinates vision perception, dual-eye animations, local SQLite memory,
motion kinematics, voice synthesis, and Gemini conversational intelligence.
"""

import sys
import time
import argparse
from pathlib import Path
from PIL import Image

from core.config import DATA_DIR, SNAPSHOTS_DIR
from core.database import AlphaDatabase
from core.eye_animator import DualEyeController, Emotion
from core.motion_controller import MotionController
from core.vision_pipeline import VisionPipeline
from core.gemini_brain import GeminiBrain
from core.voice_engine import VoiceEngine, WallESoundSynthesizer

class AlphaRobot:
    """The unified physical and cognitive robot instance."""

    def __init__(self, voice_enabled: bool = True):
        print("=" * 65)
        print("  PROJECT ALPHA: WALL-E AUTONOMOUS COMPANION ROVER")
        print("=" * 65)

        self.db = AlphaDatabase()
        self.eyes = DualEyeController()
        self.motion = MotionController()
        self.vision = VisionPipeline()
        self.voice = VoiceEngine(voice_enabled=voice_enabled)
        self.brain = GeminiBrain(db=self.db)

        # Wire up speech synchronization with eyes
        self.voice.on_speech_start = lambda: self.eyes.talking_pulse(cycles=1)

        # Seed initial facts if fresh database
        self._seed_initial_profile()

        # Play startup greeting chime & nod
        self.voice.play_sound("startup")
        self.eyes.set_emotion(Emotion.HAPPY)
        self.motion.nod(repeats=1)

    def _seed_initial_profile(self) -> None:
        """Seeds initial user profile facts if empty."""
        facts = self.db.get_user_facts()
        if not facts:
            self.db.learn_fact("user", "Akhil is the creator and companion of Project Alpha.")
            self.db.learn_fact("project", "Building a Wall-E inspired autonomous rover.")
            self.db.learn_fact("location", "Located in Kerala, India.")

    def run_cli_chat(self, voice_output: bool = True) -> None:
        """Interactive terminal session testing continuous memory, voice, and AI brain."""
        self.voice.voice_enabled = voice_output
        print("\n[ALPHA IS READY TO CHAT!]")
        print(f"Voice Output: {'ENABLED (TTS + Wall-E Chimes)' if voice_output else 'MUTED'}")
        print("Commands: 'exit' | 'facts' | 'history' | 'eyes <emotion>' | 'sound <name>' | 'voice on/off'\n")

        self.eyes.set_emotion(Emotion.HAPPY)

        while True:
            try:
                user_input = input("You > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Alpha > Beep-boop! Goodbye, Akhil! Powering down into low-power idle.")
                    self.eyes.set_emotion(Emotion.SLEEPY)
                    self.voice.play_sound("shutdown", async_play=False)
                    break
                elif user_input.lower() == "facts":
                    facts = self.db.get_user_facts()
                    print("\n--- What Alpha Currently Remembers About You ---")
                    for f in facts:
                        print(f" • [{f['category'].upper()}]: {f['fact']}")
                    print("------------------------------------------------\n")
                    continue
                elif user_input.lower() == "history":
                    history = self.db.get_recent_chat(limit=8)
                    print("\n--- Recent Chat History ---")
                    for h in history:
                        print(f"[{h['role'].upper()}]: {h['message']}")
                    print("---------------------------\n")
                    continue
                elif user_input.lower() == "voice on":
                    self.voice.voice_enabled = True
                    print("[Alpha Voice]: Voice TTS enabled.")
                    self.voice.play_sound("happy")
                    continue
                elif user_input.lower() == "voice off":
                    self.voice.voice_enabled = False
                    print("[Alpha Voice]: Voice TTS muted.")
                    continue
                elif user_input.lower().startswith("sound "):
                    snd_name = user_input.split(maxsplit=1)[1].strip()
                    self.voice.play_sound(snd_name)
                    print(f"[Alpha Sound]: Playing sound preset '{snd_name}'.")
                    continue
                elif user_input.lower().startswith("eyes "):
                    emo_str = user_input.split(maxsplit=1)[1].strip().lower()
                    emo = Emotion.from_str(emo_str)
                    self.eyes.set_emotion(emo)
                    self.motion.express_emotion(emo)
                    print(f"[Alpha Eyes]: Switched expression to {emo.name}")
                    continue

                # Generate conversational response with emotion & sound
                self.eyes.set_emotion(Emotion.ANALYZING)
                chat_res = self.brain.chat_with_emotion(user_input)
                reply = chat_res["reply"]
                emo = chat_res["emotion"]
                sound_cue = chat_res.get("sound_cue", "happy")

                # Synchronize expression, gesture, and speech
                self.eyes.set_emotion(emo)
                self.motion.express_emotion(emo)
                self.voice.speak(reply, emotion=emo, with_chirp=True)

                print(f"Alpha [{emo.value.upper()}] > {reply}\n")
            except (KeyboardInterrupt, EOFError):
                print("\n[Alpha] Session interrupted. Shutting down safely.")
                self.voice.play_sound("shutdown", async_play=False)
                break

    def export_eye_previews(self) -> None:
        """Renders and saves dual-eye preview images across all 16 emotional states."""
        print(f"\n[Alpha] Generating complete eye expression previews in: {SNAPSHOTS_DIR}")

        all_emotions = list(Emotion)
        for emo in all_emotions:
            self.eyes.set_emotion(emo)
            left_img, right_img = self.eyes.render_eyes()

            # Stitch Left and Right eyes side-by-side (with a 20px nose bridge gap)
            combined_w = 240 * 2 + 20
            combined_h = 240
            canvas = Image.new("RGB", (combined_w, combined_h), (10, 10, 14))
            canvas.paste(left_img, (0, 0))
            canvas.paste(right_img, (240 + 20, 0))

            output_file = SNAPSHOTS_DIR / f"eyes_{emo.value}.png"
            canvas.save(output_file)
            print(f"  [OK] Saved: eyes_{emo.value}.png")

        print("[Alpha] All 16 eye previews exported successfully!\n")

    def run_autonomous_loop(self) -> None:
        """The main autonomous sensory & roaming loop."""
        print("\n[Alpha] Starting Autonomous Roaming & Face Tracking Loop...")
        print("Press Ctrl+C to stop.\n")

        self.eyes.set_emotion(Emotion.IDLE)
        last_blink = time.time()
        was_tracking_face = False

        try:
            while True:
                # 1. Natural periodic eye blink (every 3 to 6 seconds)
                if time.time() - last_blink > 4.5:
                    self.eyes.blink()
                    last_blink = time.time()

                # 2. Vision Perception: Face Tracking
                face_found, fx, fy = self.vision.detect_face()
                if face_found:
                    if not was_tracking_face:
                        self.voice.play_sound("curious")
                        was_tracking_face = True
                    self.eyes.set_emotion(Emotion.HAPPY)
                    # Gaze directly at the user's face
                    self.eyes.set_gaze(fx, fy)
                    # Turn neck servos to keep face centered
                    target_pan = fx * 45.0
                    target_tilt = -fy * 25.0
                    self.motion.set_head_pose(target_pan, target_tilt)
                else:
                    if was_tracking_face:
                        was_tracking_face = False
                    self.eyes.set_emotion(Emotion.IDLE)
                    self.eyes.set_gaze(0.0, 0.0)

                # 3. Desk Cliff Edge Check
                if self.motion.check_cliff_sensors():
                    self.eyes.set_emotion(Emotion.ALERT)
                    self.voice.play_sound("alert")
                    self.motion.alert_recoil()
                    self.motion.stop()

                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[Alpha] Autonomous loop stopped by user.")
            self.voice.play_sound("shutdown", async_play=False)
        finally:
            self.motion.cleanup()
            self.vision.release()

def main():
    parser = argparse.ArgumentParser(description="Project Alpha: Wall-E Autonomous Rover Daemon")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI conversation session")
    parser.add_argument("--voice", action="store_true", help="Enable spoken voice output during CLI chat")
    parser.add_argument("--preview-eyes", action="store_true", help="Export sample PNG renders of eye expressions")
    args = parser.parse_args()

    robot = AlphaRobot(voice_enabled=args.voice or not args.cli)

    if args.preview_eyes:
        robot.export_eye_previews()
    elif args.cli:
        robot.run_cli_chat(voice_output=args.voice)
    else:
        robot.run_autonomous_loop()

if __name__ == "__main__":
    main()
