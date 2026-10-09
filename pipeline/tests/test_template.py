"""The copyable source template keeps the adapter contract and stays out of the registry."""
from __future__ import annotations

import pytest

from pipeline.etl.sources.registry import ADAPTERS


def test_template_matches_adapter_contract(tmp_path):
    from pipeline.etl.sources._template.adapter import TemplateAdapter

    adapter = TemplateAdapter()
    assert adapter.source_name == "template" and adapter.source_system == "template"
    assert callable(adapter.parse)
    assert adapter.discover(tmp_path) == []
    assert "template" not in ADAPTERS


def test_template_extract_says_fill_in(tmp_path):
    from pipeline.etl.sources._template import extract

    with pytest.raises(NotImplementedError, match="FILL IN"):
        extract.pull_season(2026, out_root=tmp_path)
