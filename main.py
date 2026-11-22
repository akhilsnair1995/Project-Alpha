"""
Project Alpha: Autonomous Desktop Companion Robot.
Main integration entry point combining vision, procedural animatronics,
physical motion control, voice synthesis, live microphone listening,
navigation cortex, and hybrid cloud/edge AI brain.
"""

import os
import sys
import time
import argparse
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    from core.eye_animator import Image

from core.config import DATA_DIR, SNAPSHOTS_DIR, ALPHA_VOICE_PATH
from core.database import AlphaDatabase
from core.eye_animator import DualEyeController, Emotion
from core.motion_controller import MotionController
from core.vision_pipeline import VisionPipeline
from core.gemini_brain import GeminiBrain
from core.voice_engine import VoiceEngine, WallESoundSynthesizer
from core.navigation_cortex import NavigationCortex, BehaviorState
from core.behavior_engine import AlphaBehaviorEngine, BehaviorAction
from core.live_listener import LiveMicrophoneListener

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
        self.vision.db = self.db
        self.voice = VoiceEngine(voice_enabled=voice_enabled)
        self.brain = GeminiBrain(db=self.db)
        self.behavior = AlphaBehaviorEngine(brain=self.brain)
        self.nav = NavigationCortex(motion_controller=self.motion, eye_controller=self.eyes, db=self.db)
        self.nav.engine.behavior_engine = self.behavior
        self.current_directive = {"action": "COMPANION_IDLE", "target": None}
        self.listener = LiveMicrophoneListener(
            voice_engine=self.voice,
            brain=self.brain,
            eyes=self.eyes,
            motion=self.motion,
            db=self.db
        )

        # Wire up speech synchronization with eyes
        self.voice.on_speech_start = lambda: self.eyes.talking_pulse(cycles=1)

        # Seed initial facts if fresh database
        self._seed_initial_profile()

        # Play startup greeting: Alpha's authentic voice clip if present, or synth chime
        if ALPHA_VOICE_PATH.exists():
            self.voice.play_alpha_voice(async_play=True)
        else:
            self.voice.play_sound("startup")
        self.eyes.set_emotion(Emotion.HAPPY)
        self.motion.nod(repeats=1)

    def _seed_initial_profile(self) -> None:
        """Disabled: Zero artificial injection. Alpha learns purely through organic interaction."""
        pass

    def run_cli_chat(self, voice_output: bool = True) -> None:
        """Interactive terminal session testing continuous memory, voice, and AI brain."""
        self.voice.voice_enabled = voice_output
        print("\n[ALPHA IS READY TO CHAT!]")
        print(f"Voice Output: {'ENABLED (TTS + Wall-E Chimes)' if voice_output else 'MUTED'}")
        print("Commands: 'exit' | 'facts' | 'history' | 'eyes <emotion>' | 'sound <name>' | 'voice on/off'\n")

        self.eyes.set_emotion(Emotion.HAPPY)
        self.listener.start()

        while True:
            try:
                user_input = input("You > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Alpha > Beep-boop! Goodbye, Akhil! Powering down into low-power idle.")
                    self.eyes.set_emotion(Emotion.SLEEPY)
                    self.voice.play_sound("shutdown", async_play=False)
                    self.listener.stop()
                    break
                elif user_input.lower() == "facts":
                    facts = self.db.get_user_facts()
                    print("\n--- What Alpha Currently Remembers About You ---")
                    for cat, fact in facts.items():
                        print(f"  • [{cat.upper()}]: {fact}")
                    print("------------------------------------------------\n")
                    continue
                elif user_input.lower() == "history":
                    chat = self.db.get_recent_chat(limit=10)
                    print("\n--- Recent Conversation History ---")
                    for msg in chat:
                        print(f"  [{msg['role'].upper()}] ({msg['brain_type']}): {msg['message']}")
                    print("------------------------------------\n")
                    continue
                elif user_input.lower().startswith("eyes "):
                    emo_name = user_input.split(" ", 1)[1].strip()
                    emo = Emotion.from_str(emo_name)
                    self.eyes.set_emotion(emo)
                    self.motion.express_emotion(emo)
                    print(f"[Alpha Eyes] Emotion set to: {emo.value.upper()}")
                    continue
                elif user_input.lower().startswith("sound "):
                    snd_name = user_input.split(" ", 1)[1].strip()
                    self.voice.play_sound(snd_name)
                    continue
                elif user_input.lower() == "voice on":
                    self.voice.voice_enabled = True
                    print("[Voice] Enabled.")
                    continue
                elif user_input.lower() == "voice off":
                    self.voice.voice_enabled = False
                    print("[Voice] Muted.")
                    continue

                # Query the AI brain with full affective memory
                chat_res = self.brain.chat_with_emotion(user_input)
                reply = chat_res["reply"]
                emo = chat_res["emotion"]
                sound_cue = chat_res.get("sound_cue", "happy")

                # Synchronize physical directive execution via Navigation Cortex
                action = chat_res.get("action")
                target = chat_res.get("target")
                if action:
                    self.nav.execute_directive(action, target)
                    self.current_directive = {"action": action, "target": target}
                    print(f"[Navigation Cortex]: Executed {action} (Target: {target}). Thought: {self.nav.current_thought}")

                # Synchronize expression, gesture, and speech
                self.eyes.set_emotion(emo)
                self.motion.express_emotion(emo)

                print(f"Alpha [{emo.value.upper()}] > {reply}")
                if self.voice.voice_enabled:
                    self.voice.speak(reply, emotion=emo.value)

            except (KeyboardInterrupt, EOFError):
                print("\n[Alpha] Chat session ended.")
                self.listener.stop()
                break

    def export_all_expression_previews(self, output_dir: Path = SNAPSHOTS_DIR) -> None:
        """Renders and saves PNG snapshots for all 16 procedural eye expressions."""
        print(f"\n[Alpha] Exporting all 16 eye expression snapshots to {output_dir}...")
        output_dir.mkdir(parents=True, exist_ok=True)

        for emo in Emotion:
            self.eyes.set_emotion(emo)
            self.eyes.set_gaze(0.0, 0.0)
            left_img, right_img = self.eyes.render_eyes()

            # Stitch both eyes side-by-side onto a 500x260 black canvas
            preview = Image.new("RGB", (500, 260), (0, 0, 0))
            preview.paste(left_img, (10, 10))
            preview.paste(right_img, (250, 10))

            file_path = output_dir / f"eyes_{emo.value}.png"
            preview.save(file_path, "PNG")
            print(f"  ✓ Exported: {file_path.name}")

        print("[Alpha] All 16 eye previews exported successfully!\n")

    def run_autonomous_loop(self, show_window: bool = True) -> None:
        """The main autonomous sensory & roaming loop driven by the behavior engine & navigation cortex."""
        print("\n[Alpha] Starting Autonomous Roaming & Face Tracking Loop...")
        if not self.motion.hardware_enabled:
            print("[Notice] Running on PC / Simulation environment.")
            print("         • To simulate Pi 5 hardware work cycle: python3 pi5_vm_simulator.py")
            print("         • To chat interactively with Alpha:     python3 main.py --cli")
            print("         • To launch browser 3D simulator:       python3 simulator/run_sim.py")
        print("Press Ctrl+C to stop.\n")

        self.eyes.set_emotion(Emotion.IDLE)
        last_heartbeat = time.time()

        try:
            while True:
                # 0. Step backend navigation cortex
                self.nav.step(0.05)

                # Periodic simulation heartbeat every 8 seconds
                if not self.motion.hardware_enabled and (time.time() - last_heartbeat > 8.0):
                    print("[Sensory Loop Heartbeat]: Scanning for face | Cliff IR active | Waiting for events...")
                    last_heartbeat = time.time()

                # 1. Vision Perception: High-stability Face Tracking
                frame = self.vision.capture_frame()
                face_res = self.vision.track_face_detailed(frame)

                # 2. Compute Emotional Response & Companion Actions
                action = self.behavior.process_vision(face_res, frame=frame, allow_speech=self.voice.voice_enabled)
                self.behavior.apply_action(self, action)

                # 3. Desk Cliff Edge Safety Check
                if self.motion.check_cliff_sensors():
                    self.eyes.set_emotion(Emotion.ALERT)
                    self.voice.play_sound("alert")
                    self.motion.alert_recoil()
                    self.motion.stop()
                    self.db.log_observation("Table cliff edge detected. Emergency stop engaged.")

                # 4. Head Petting Touch Reaction (TTP223)
                if self.motion.is_head_touched():
                    self.eyes.set_emotion(Emotion.LOVE)
                    self.voice.play_sound("love")
                    self.motion.head_pet_reaction()

                # 5. Charging Dock Engagement Detection (GPIO 26)
                if self.motion.is_dock_charging():
                    self.eyes.set_emotion(Emotion.SLEEPY)
                    self.voice.play_sound("startup")
                    self.motion.stop()

                # 6. Optional Live Window HUD preview in simulation mode
                if show_window and frame is not None:
                    try:
                        import cv2
                        hud = self.vision.draw_hud(frame, face_res, action.state, action.emotion)
                        cv2.imshow("Project Alpha - Laptop Camera Vision Cortex", hud)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (27, ord('q')):
                            break
                        if cv2.getWindowProperty("Project Alpha - Laptop Camera Vision Cortex", cv2.WND_PROP_VISIBLE) < 1:
                            print("[Alpha] Camera window closed by user.")
                            break
                    except Exception:
                        pass

                time.sleep(0.035)
        except KeyboardInterrupt:
            print("\n[Alpha] Autonomous loop stopped by user.")
            self.voice.play_sound("shutdown", async_play=False)
        finally:
            try:
                import cv2
                cv2.destroyAllWindows()
            except Exception:
                pass
            self.listener.stop()
            self.motion.cleanup()
            self.vision.release()

def main():
    parser = argparse.ArgumentParser(description="Project Alpha: Wall-E Autonomous Companion Robot")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI conversation session")
    parser.add_argument("--voice", action="store_true", help="Enable spoken voice output during CLI chat")
    parser.add_argument("--preview-eyes", action="store_true", help="Export sample PNG renders of eye expressions")
    parser.add_argument("--no-view", dest="view", action="store_false", default=True, help="Disable OpenCV camera HUD window")
    args = parser.parse_args()

    robot = AlphaRobot(voice_enabled=args.voice or not args.cli)

    if args.preview_eyes:
        robot.export_all_expression_previews()
    elif args.cli:
        robot.run_cli_chat(voice_output=args.voice)
    else:
        robot.run_autonomous_loop(show_window=args.view)

if __name__ == "__main__":
    main()
