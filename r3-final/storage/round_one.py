"""Round-one editable format and its full, backwards-compatible record view."""
from copy import deepcopy

from . import editorial_defaults, relation_indexes, source_catalog


STORAGE_PROFILE = "pipl-single-source-r1"
LEGACY_VERSION = "4.1-role-label-preview"


def catalog_counts(model):
    return {
        "source_fragments": len(model["source_fragments"]),
        "legal_relations": len(model["legal_relations"]),
        "exception_records": len(model["exceptions"]),
        "effect_templates": sum(len(record["effects"]) for record in model["records"]),
    }


def compact(source):
    if "storage_profile" in source or source.get("schema_version") != LEGACY_VERSION:
        raise ValueError(f"Expected the expanded {LEGACY_VERSION} model")
    model = deepcopy(source)
    for key, value in catalog_counts(model).items():
        if model["statistics"].pop(key) != value:
            raise ValueError(f"statistics.{key} disagrees with the underlying data")
    source_catalog.compact(model)
    relation_indexes.compact(model)
    editorial_defaults.compact(model)
    model["storage_profile"] = STORAGE_PROFILE
    return model


def expand(source):
    if source.get("storage_profile") != STORAGE_PROFILE:
        raise ValueError(f"Expected storage_profile {STORAGE_PROFILE}")
    model = deepcopy(source)
    del model["storage_profile"]
    source_catalog.expand(model)
    relation_indexes.expand(model)
    editorial_defaults.expand(model)
    for key, value in catalog_counts(model).items():
        if key in model["statistics"]:
            raise ValueError(f"Duplicate derived statistics.{key}")
        model["statistics"][key] = value
    return model


def for_export(source):
    """Accept the new storage profile and preserve the older exporter's input API."""
    return expand(source) if "storage_profile" in source else source
