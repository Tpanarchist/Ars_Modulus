"""Verify that the Ars Modulus experimental substrate is available."""

from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import sys
import tempfile


def main() -> None:
    assert sys.version_info[:2] == (3, 13), (
        f"Python 3.13 required; found {sys.version.split()[0]}"
    )

    project_root = Path(__file__).resolve().parents[1]
    palette_path = project_root / "assets" / "lacking64.json"

    # Keep DSPy's eager disk cache out of the user's home directory.
    with tempfile.TemporaryDirectory(prefix="ars-modulus-smoke-") as cache_dir:
        os.environ["DSPY_CACHEDIR"] = cache_dir
        import dspy

        dspy.cache.disk_cache.close()
        dspy.configure_cache(enable_disk_cache=False)

    # txtai probes its optional LiteLLM backend during import. DSPy installs
    # LiteLLM, whose import can fetch tokenizer data. The base txtai import is
    # all this offline substrate check requires, so hide that optional backend.
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    missing = object()
    previous_litellm = sys.modules.get("litellm", missing)
    sys.modules["litellm"] = None
    try:
        import txtai
    finally:
        if previous_litellm is missing:
            sys.modules.pop("litellm", None)
        else:
            sys.modules["litellm"] = previous_litellm

    import simpleaichat
    import textual

    with palette_path.open(encoding="utf-8") as palette_file:
        palette = json.load(palette_file)

    colors = palette["colors"]
    assert len(colors) == 64, f"Expected 64 colors; found {len(colors)}"
    assert len(set(colors)) == 64, "LACKING64 colors must be unique"

    print(f"Python: {sys.version.split()[0]}")
    distributions = (
        ("simpleaichat", simpleaichat),
        ("dspy", dspy),
        ("txtai", txtai),
        ("textual", textual),
    )
    for distribution_name, module in distributions:
        try:
            detected_version = version(distribution_name)
        except PackageNotFoundError:
            detected_version = getattr(module, "__version__", "unknown")
        print(f"{distribution_name}: {detected_version}")

    print(
        f"Palette: {palette['name']} by {palette['author']} "
        f"({len(colors)} unique colors)"
    )


if __name__ == "__main__":
    main()
