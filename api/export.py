"""python -m api.export : write api/openapi.json (the contract the web app's types are generated from)."""
import json
from pathlib import Path

from api.main import app

path = Path(__file__).resolve().parent / "openapi.json"
path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", path, f"({len(app.openapi()['paths'])} paths)")
