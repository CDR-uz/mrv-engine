"""Reading batches off disk.

Kept out of `core` deliberately: the core takes a `Batch`, never a path.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from mrv_engine.core.factors import FactorSet
from mrv_engine.core.models import Batch
from mrv_engine.core.rules import RulePack

def _shipped(directory: str, name: str) -> Path:
    """Locate a pack that ships with the engine.

    In a source checkout the packs sit at the repository root, which is where a
    reader looks for them. In an installed wheel the same files are copied under
    the package. Preferring the checkout means editing a pack in a working tree
    takes effect without reinstalling.
    """
    checkout = Path(__file__).resolve().parents[3] / directory / name
    if checkout.is_file():
        return checkout
    return Path(str(resources.files("mrv_engine") / "_packs" / directory / name))


DEFAULT_FACTORS = _shipped("factors", "default.yaml")
DEFAULT_RULES = _shipped("rules", "generic_biochar.yaml")


def load_batch(path: str | Path) -> Batch:
    """Load a batch from a YAML or JSON file.

    Validation errors are left to propagate as pydantic raises them: they name
    the offending field and are more useful than anything wrapped around them.
    """
    text = Path(path).read_text(encoding="utf-8")
    return Batch.model_validate(yaml.safe_load(text))


def load_factors(path: str | Path | None = None) -> FactorSet:
    """Load a factor set, defaulting to the placeholder set shipped in-tree."""
    text = Path(path or DEFAULT_FACTORS).read_text(encoding="utf-8")
    return FactorSet.model_validate(yaml.safe_load(text))


def load_rules(path: str | Path | None = None) -> RulePack:
    """Load a rule pack, defaulting to the generic biochar pack shipped in-tree."""
    text = Path(path or DEFAULT_RULES).read_text(encoding="utf-8")
    return RulePack.model_validate(yaml.safe_load(text))
