"""Reading batches off disk.

Kept out of `core` deliberately: the core takes a `Batch`, never a path.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from cacarbon_mrv.core.models import Batch


def load_batch(path: str | Path) -> Batch:
    """Load a batch from a YAML or JSON file.

    Validation errors are left to propagate as pydantic raises them: they name
    the offending field and are more useful than anything wrapped around them.
    """
    text = Path(path).read_text(encoding="utf-8")
    return Batch.model_validate(yaml.safe_load(text))
