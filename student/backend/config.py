
import os
from pathlib import Path

# Trigger Server Reload (Fix Validation)

def load_api_key():
    """
    Robustly loads Gemini API Key from multiple sources:
    1. Environment Variable 'GEMINI_API_KEY' (Best Practice)
    2. .env file in project root or backend dir
    3. 'Gemini_key' file (Legacy)
    """
    # 1. Check Env Var
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()

    # Define potential paths
    base_dir = Path(__file__).parent.parent # student/
    paths_to_check = [
        base_dir / ".env",
        base_dir / "backend" / ".env",
        base_dir / "Gemini_key",
        Path("Gemini_key") # CWD fallback
    ]

    for path in paths_to_check:
        if path.exists():
            try:
                content = path.read_text().strip()
                # If .env, parse it roughly (or use python-dotenv if installed)
                if path.suffix == ".env":
                    for line in content.splitlines():
                        if line.startswith("GEMINI_API_KEY="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
                else:
                    return content
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}")

    return None

API_KEY = load_api_key()
