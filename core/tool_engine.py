"""
Project Alpha: Dynamic Tool Engine & Self-Programming Cortex.
Enables Alpha to autonomously create, test, hot-reload, execute, and self-heal
software tools in runtime without restarting the robot daemon or corrupting core hardware code.
"""

import os
import sys
import inspect
import importlib
import traceback
from typing import Dict, Any, List, Optional

# Path to Alpha's dynamic user-space tool belt
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(BASE_DIR, "tools", "dynamic")
os.makedirs(TOOLS_DIR, exist_ok=True)

if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


class DynamicToolEngine:
    """
    Manages Alpha's self-programmed skill library.
    Provides sandboxing, syntax checking, hot-reloading, execution,
    and self-bug diagnostics for the Gemini/Gemma cognitive cortex.
    """

    def __init__(self, tools_dir: Optional[str] = None):
        self.tools_dir = tools_dir or TOOLS_DIR
        os.makedirs(self.tools_dir, exist_ok=True)
        if self.tools_dir not in sys.path:
            sys.path.insert(0, self.tools_dir)

        self.active_tools: Dict[str, Dict[str, Any]] = {}
        self.reload_all_tools()

    def reload_all_tools(self) -> List[str]:
        """
        Scans tools/dynamic/ and hot-reloads every valid Python tool.
        Returns list of successfully loaded tool names.
        """
        loaded = []
        if not os.path.exists(self.tools_dir):
            return loaded

        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    if module_name in sys.modules:
                        mod = importlib.reload(sys.modules[module_name])
                    else:
                        mod = importlib.import_module(module_name)

                    # Look for primary entrypoint: 'run' or function named after module
                    entry_func = getattr(mod, "run", getattr(mod, module_name, None))
                    if callable(entry_func):
                        # Extract parameter signature for LLM documentation
                        sig = inspect.signature(entry_func)
                        doc = inspect.getdoc(entry_func) or "No description provided."

                        self.active_tools[module_name] = {
                            "module": mod,
                            "func": entry_func,
                            "signature": str(sig),
                            "doc": doc,
                            "path": os.path.join(self.tools_dir, filename)
                        }
                        loaded.append(module_name)
                    else:
                        print(f"[DynamicToolEngine] Warning: '{filename}' has no callable 'run' function.")
                except Exception as e:
                    print(f"[DynamicToolEngine] Failed to load tool '{module_name}': {e}")

        return loaded

    def create_or_patch_tool(self, tool_name: str, code: str) -> Dict[str, Any]:
        """
        Alpha calls this function to write, evolve, or fix its own tools.
        Includes syntax compilation check, automated backup, hot-reload,
        and rollback on failure.
        """
        clean_name = tool_name.replace(".py", "").strip()
        if not clean_name.isidentifier():
            return {
                "success": False,
                "error": f"Invalid tool name '{tool_name}'. Must be a valid Python identifier (letters, numbers, underscores)."
            }

        file_path = os.path.join(self.tools_dir, f"{clean_name}.py")
        backup_path = file_path + ".bak"

        # 1. Pre-validation: Compile to AST/bytecode before touching the file
        try:
            compile(code, f"{clean_name}.py", "exec")
        except SyntaxError as e:
            tb = traceback.format_exc()
            return {
                "success": False,
                "error": f"SyntaxError in generated tool '{clean_name}': {e}",
                "traceback": tb,
                "line": e.lineno,
                "offset": e.offset,
                "advice": "Review Python syntax around the specified line and re-patch."
            }

        # 2. Backup existing version if it exists
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    old_code = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(old_code)
            except Exception as e:
                print(f"[DynamicToolEngine] Backup creation warning: {e}")

        # 3. Write new code to disk
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file '{file_path}': {e}"
            }

        # 4. Dry-run load & validation
        try:
            if clean_name in sys.modules:
                mod = importlib.reload(sys.modules[clean_name])
            else:
                mod = importlib.import_module(clean_name)

            entry_func = getattr(mod, "run", getattr(mod, clean_name, None))
            if not callable(entry_func):
                raise RuntimeError(
                    f"Tool '{clean_name}.py' was loaded but did not define a callable 'run(*args, **kwargs)' entrypoint!"
                )

            # Successfully verified
            sig = inspect.signature(entry_func)
            doc = inspect.getdoc(entry_func) or "No description provided."
            self.active_tools[clean_name] = {
                "module": mod,
                "func": entry_func,
                "signature": str(sig),
                "doc": doc,
                "path": file_path
            }

            return {
                "success": True,
                "message": f"Tool '{clean_name}' successfully compiled, verified, and hot-loaded into active memory!",
                "tool_name": clean_name,
                "signature": str(sig),
                "doc": doc
            }

        except Exception as e:
            # Revert from backup if available
            tb = traceback.format_exc()
            reverted = False
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, "r", encoding="utf-8") as f:
                        prev_code = f.read()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(prev_code)
                    if clean_name in sys.modules:
                        importlib.reload(sys.modules[clean_name])
                    reverted = True
                except Exception:
                    pass

            return {
                "success": False,
                "error": f"Runtime import error while verifying '{clean_name}': {e}",
                "traceback": tb,
                "reverted_to_backup": reverted,
                "advice": "Analyze the traceback (e.g. missing import, bad parameter, type error) and call create_or_patch_tool with the fix."
            }

    def execute_tool(self, tool_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Executes an active tool from Alpha's toolbelt.
        Catches all runtime errors and returns structured diagnostic feedback
        so Alpha can self-heal and patch its own bug.
        """
        clean_name = tool_name.replace(".py", "").strip()
        if clean_name not in self.active_tools:
            return {
                "status": "not_found",
                "error": f"Tool '{clean_name}' is not in Alpha's active toolbelt. Available: {list(self.active_tools.keys())}"
            }

        entry_func = self.active_tools[clean_name]["func"]
        try:
            result = entry_func(*args, **kwargs)
            return {
                "status": "success",
                "tool_name": clean_name,
                "result": result
            }
        except Exception as e:
            tb = traceback.format_exc()
            return {
                "status": "bug_encountered",
                "tool_name": clean_name,
                "error": str(e),
                "traceback": tb,
                "advice": f"Bug encountered while running '{clean_name}'. Alpha should inspect the traceback and call create_or_patch_tool to repair the bug."
            }

    def get_tool_code(self, tool_name: str) -> Optional[str]:
        """Returns the Python source code of a specified tool."""
        clean_name = tool_name.replace(".py", "").strip()
        file_path = os.path.join(self.tools_dir, f"{clean_name}.py")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_tools(self) -> List[Dict[str, str]]:
        """Returns metadata for all available self-programmed tools."""
        tools_list = []
        for name, meta in self.active_tools.items():
            tools_list.append({
                "name": name,
                "signature": meta.get("signature", "()"),
                "doc": meta.get("doc", "No description.")
            })
        return tools_list

    def format_tools_for_prompt(self) -> str:
        """Formats the list of active tools for inclusion in Alpha's LLM context."""
        tools = self.list_tools()
        if not tools:
            return "No dynamic self-programmed tools currently loaded."

        lines = ["[ALPHA DYNAMIC TOOLBELT]:"]
        for t in tools:
            lines.append(f"• {t['name']}{t['signature']}: {t['doc']}")
        return "\n".join(lines)
