"""Write the API contract to backend/openapi.json. The frontend client is generated from it."""

import json
from pathlib import Path

from app.main import app

out = Path(__file__).parent.parent / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
print(f"wrote {out}")
