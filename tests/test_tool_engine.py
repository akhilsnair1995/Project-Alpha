"""
tests/test_tool_engine.py
Unit tests for Alpha's DynamicToolEngine, self-programming, and self-healing cortex.
"""

import os
import shutil
import tempfile
from pathlib import Path
import unittest

from core.tool_engine import DynamicToolEngine
from core.gemini_brain import HybridBrain
from core.database import AlphaDatabase


class TestDynamicToolEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary sandbox directory for test tools
        self.test_dir = tempfile.mkdtemp(prefix="alpha_test_tools_")
        self.engine = DynamicToolEngine(tools_dir=self.test_dir)

    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_and_load_valid_tool(self):
        """Alpha creates a valid tool, hot-reloads it, and executes it."""
        code = '''"""Test adder tool."""
def run(a: int, b: int) -> dict:
    return {"sum": a + b}
'''
        res = self.engine.create_or_patch_tool("test_adder", code)
        self.assertTrue(res["success"], f"Failed to create tool: {res}")
        self.assertIn("test_adder", self.engine.active_tools)

        # Execute tool
        exec_res = self.engine.execute_tool("test_adder", a=15, b=27)
        self.assertEqual(exec_res["status"], "success")
        self.assertEqual(exec_res["result"], {"sum": 42})

    def test_syntax_error_rejection(self):
        """Alpha catches syntax errors before file corruption."""
        bad_code = "def run(:\n    return False"
        res = self.engine.create_or_patch_tool("bad_syntax", bad_code)
        self.assertFalse(res["success"])
        self.assertIn("SyntaxError", res["error"])
        self.assertNotIn("bad_syntax", self.engine.active_tools)

    def test_missing_run_function_rejection(self):
        """Tool without entrypoint 'run' is rejected and rolled back."""
        code = "x = 42\ny = 100"
        res = self.engine.create_or_patch_tool("no_run_func", code)
        self.assertFalse(res["success"])
        self.assertIn("callable 'run", res["error"])

    def test_runtime_bug_detection_and_self_healing(self):
        """Tool encounters a ZeroDivisionError, reports traceback, and Alpha self-heals it with a patch."""
        # 1. Buggy version
        buggy_code = '''def run(val: int) -> dict:
    return {"result": 100 / val}
'''
        res = self.engine.create_or_patch_tool("safe_divider", buggy_code)
        self.assertTrue(res["success"])

        # Execute with zero -> triggers bug
        exec_res = self.engine.execute_tool("safe_divider", val=0)
        self.assertEqual(exec_res["status"], "bug_encountered")
        self.assertIn("division by zero", exec_res["error"])
        self.assertIn("Traceback", exec_res["traceback"])

        # 2. Alpha patches the tool with a fix
        patched_code = '''def run(val: int) -> dict:
    if val == 0:
        return {"result": None, "warning": "Cannot divide by zero"}
    return {"result": 100 / val}
'''
        patch_res = self.engine.create_or_patch_tool("safe_divider", patched_code)
        self.assertTrue(patch_res["success"])

        # Re-execute -> now succeeds safely!
        healed_res = self.engine.execute_tool("safe_divider", val=0)
        self.assertEqual(healed_res["status"], "success")
        self.assertIsNone(healed_res["result"]["result"])
        self.assertEqual(healed_res["result"]["warning"], "Cannot divide by zero")

    def test_rollback_on_broken_patch(self):
        """If a patch introduces an import error, engine rolls back to previous valid backup."""
        good_code = '''def run() -> dict:
    return {"state": "healthy"}
'''
        self.engine.create_or_patch_tool("fragile_tool", good_code)

        # Attempt to patch with a broken module import
        broken_patch = '''import non_existent_super_module_xyz
def run():
    return {}
'''
        patch_res = self.engine.create_or_patch_tool("fragile_tool", broken_patch)
        self.assertFalse(patch_res["success"])
        self.assertTrue(patch_res.get("reverted_to_backup"))

        # Verify previous working version still runs
        prev_res = self.engine.execute_tool("fragile_tool")
        self.assertEqual(prev_res["status"], "success")
        self.assertEqual(prev_res["result"]["state"], "healthy")

    def test_tool_prompt_formatting(self):
        """Tool engine formats active tools cleanly for LLM system prompt context."""
        code = '''def run(angle_deg: float) -> dict:
    """Calculates servo turn impulse."""
    return {"turn": angle_deg}
'''
        self.engine.create_or_patch_tool("turn_calculator", code)
        prompt_str = self.engine.format_tools_for_prompt()
        self.assertIn("[ALPHA DYNAMIC TOOLBELT]:", prompt_str)
        self.assertIn("turn_calculator", prompt_str)
        self.assertIn("Calculates servo turn impulse.", prompt_str)


class TestHybridBrainToolIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_brain_mem.db"
        self.db = AlphaDatabase(db_path=self.db_path)
        self.brain = HybridBrain(db=self.db)

    def tearDown(self):
        if hasattr(self, "brain") and hasattr(self.brain, "tool_engine"):
            for p in Path(self.brain.tool_engine.tools_dir).glob("calculate_circle_circumference*"):
                try:
                    p.unlink()
                except Exception:
                    pass
        self.temp_dir.cleanup()

    def test_brain_has_tool_engine(self):
        """HybridBrain initializes with DynamicToolEngine and starter tools."""
        self.assertTrue(hasattr(self.brain, "tool_engine"))
        tools = self.brain.list_tools()
        self.assertIsInstance(tools, list)
        tool_names = [t["name"] for t in tools]
        self.assertIn("spatial_rangefinder", tool_names)
        self.assertIn("contrast_booster", tool_names)

    def test_chat_tool_listing_interceptor(self):
        """User asks 'what tools do you have' and Alpha answers from its toolbelt."""
        res = self.brain.chat_with_emotion("Alpha, what tools do you have in your toolbelt?")
        self.assertEqual(res["brain_type"], "local_toolbelt")
        self.assertIn("spatial_rangefinder", res["reply"])

    def test_chat_tool_execution_interceptor(self):
        """User asks Alpha to run a tool, and Alpha executes it and reports the result."""
        res = self.brain.chat_with_emotion("run tool contrast_booster")
        self.assertEqual(res["brain_type"], "tool_execution")
        self.assertIn("Executed 'contrast_booster'", res["reply"])

    def test_evolve_tool_from_need(self):
        """Alpha autonomously synthesizes and tests a tool based on a capability description."""
        res = self.brain.evolve_tool_from_need("calculate circle circumference given radius")
        self.assertTrue(res["success"])
        self.assertIn(res["tool_name"], [t["name"] for t in self.brain.list_tools()])


if __name__ == "__main__":
    unittest.main()
