import ast
import tempfile
import subprocess
import sys
import os
import shutil

FORBIDDEN_IMPORTS = {'os', 'sys', 'subprocess', 'shutil', 'pty', 'pathlib', 'socket', 'threading', 'multiprocessing', 'importlib', 'pickle', 'urllib', 'requests', 'http', 'ftplib', 'telnetlib'}
FORBIDDEN_FUNCTIONS = {'open', 'eval', 'exec', 'compile', '__import__', 'globals', 'locals', 'vars', 'getattr', 'setattr', 'delattr', 'memoryview', 'input'}

class SecurityScanner(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split('.')[0] in FORBIDDEN_IMPORTS:
                self.errors.append(f"Security Error: Import of '{alias.name}' is blocked.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in FORBIDDEN_IMPORTS:
            self.errors.append(f"Security Error: Import from '{node.module}' is blocked.")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_FUNCTIONS:
                self.errors.append(f"Security Error: Function '{node.func.id}()' is blocked.")
        self.generic_visit(node)

def is_safe_python(code: str) -> tuple[bool, str]:
    """Uses AST to scan for dangerous imports and builtins before execution."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {str(e)}"
    
    scanner = SecurityScanner()
    scanner.visit(tree)
    if scanner.errors:
        return False, "\n".join(scanner.errors)
    return True, ""

def check_node_available():
    return shutil.which("node") is not None

def execute_code(code: str, language: str = "Python", timeout: int = 10) -> dict:
    """
    Runs code in a subprocess with a timeout.
    Supports Python (with AST sandboxing) and JavaScript.
    """
    if language == "Python":
        safe, msg = is_safe_python(code)
        if not safe:
            return {"stdout": "", "stderr": msg, "success": False}
            
        suffix = ".py"
        cmd_runner = [sys.executable]
    elif language == "JavaScript":
        if not check_node_available():
            return {
                "stdout": "",
                "stderr": "Node.js is not installed. Install it from https://nodejs.org/",
                "success": False
            }
        suffix = ".js"
        cmd_runner = ["node"]
    else:
        return {
            "stdout": "", 
            "stderr": f"Execution for {language} is not supported locally.", 
            "success": False
        }

    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name
        
    try:
        cmd = cmd_runner + [tmp_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"⏱️ Execution timed out after {timeout}s. Your code may have an infinite loop.",
            "success": False,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "success": False}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
