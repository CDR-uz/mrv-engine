"""Reading batches off disk.

Kept out of `core` deliberately: the core takes a `Batch`, never a path.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mrv_engine.core.factors import FactorSet
from mrv_engine.core.models import Batch

DEFAULT_FACTORS = Path(__file__).resolve().parents[3] / "factors" / "default.yaml"


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
