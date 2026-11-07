"""Regenerate schema/registry.schema.json from freemyid.models.Registry. OWNER: orchestrator."""
import json
from pathlib import Path

from freemyid.models import Registry, StateLawRegistry
from freemyid.setup_config import SetupConfig

root = Path(__file__).resolve().parent.parent
(root / "schema" / "registry.schema.json").write_text(
    json.dumps(Registry.model_json_schema(), indent=2) + "\n")
(root / "schema" / "state_laws.schema.json").write_text(
    json.dumps(StateLawRegistry.model_json_schema(), indent=2) + "\n")
setup = SetupConfig.model_json_schema()
setup = {"$schema": "https://json-schema.org/draft/2020-12/schema",
         "$id": "https://freemyid.org/schema/setup-config.schema.json", **setup}
(root / "schema" / "setup-config.schema.json").write_text(json.dumps(setup, indent=2) + "\n")
print("schemas written")
