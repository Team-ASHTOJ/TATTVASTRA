import json
from importlib.resources import files

from jocky_contracts.status import CapabilityStatus


def load_coverage() -> list[CapabilityStatus]:
    resource = files("jocky_control_plane").joinpath("data/requirements.json")
    entries = json.loads(resource.read_text(encoding="utf-8"))
    return [CapabilityStatus.model_validate(entry) for entry in entries]
