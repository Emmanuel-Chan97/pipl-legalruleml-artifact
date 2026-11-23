"""Project editorial display categories without changing legal functions or native elements."""

# Migration seeds for the PIPL edition's Chinese browsing taxonomy.
# The editable R3 model owns the resulting maps.
FUNCTION_DEFAULTS = {
    "exemption": "许可与豁免",
    "necessary_condition": "适用与定义",
    "legal_position": "权利",
    "statutory_duty": "义务",
    "liability_consequence": "法律责任",
    "validity_condition": "适用与定义",
    "definition": "适用与定义",
    "applicability": "适用与定义",
    "temporal_rule": "适用与定义",
    "procedural_entitlement": "权利",
    "principle": "原则背景",
    "legislative_purpose": "制度与立法背景",
    "policy_framework": "制度与立法背景",
}

CONDUCT_DEFAULTS = {
    "lrml:Obligation": "义务",
    "lrml:Prohibition": "禁止",
    "lrml:Permission": "许可与豁免",
}


def _default_category(display, record):
    function = record["rule_function"]
    if function == "conduct_requirement":
        element = record["legalruleml"].get("native_element")
        return display["by_conduct_element"].get(element)
    return display["by_function"].get(function)


def category_for(model, record):
    """Resolve the single display category, accepting R2 input as well."""
    if "display_categories" not in model:
        return record["category"]
    display = model["display_categories"]
    record_id = record["id"]
    if record_id in display["by_record"]:
        label = display["by_record"][record_id]
    else:
        label = _default_category(display, record)
    if not isinstance(label, str) or not label.strip():
        raise ValueError(f"display_categories.by_record[{record_id!r}]: choose an explicit display category")
    return label


def compact(model):
    """Move R2's materialised categories into an R3 browsing policy."""
    if "display_categories" in model:
        raise ValueError("display_categories already exists")
    display = {
        "by_function": FUNCTION_DEFAULTS.copy(),
        "by_conduct_element": CONDUCT_DEFAULTS.copy(),
        "by_record": {},
    }
    seen = set()
    for record in model["records"]:
        record_id = record["id"]
        label = record["category"]
        if record_id in seen:
            raise ValueError(f"Duplicate record id {record_id!r} in classification")
        seen.add(record_id)
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"{record_id}.category: expected a nonempty display label")
        if label != _default_category(display, record):
            display["by_record"][record_id] = label
    for record in model["records"]:
        del record["category"]
    model["display_categories"] = display


def expand(model):
    """Restore the exact single-label R2 browsing view for existing readers."""
    display = model["display_categories"]
    records = model["records"]
    record_ids = {record["id"] for record in records}
    if len(records) != len(record_ids):
        raise ValueError("Duplicate record id in classification")
    unknown = set(display["by_record"]) - record_ids
    if unknown:
        raise ValueError(f"display_categories.by_record references unknown records: {sorted(unknown)}")
    labels = []
    for record in records:
        if "category" in record:
            raise ValueError(f"{record['id']}.category conflicts with display_categories")
        labels.append(category_for(model, record))
    for record, label in zip(records, labels):
        record["category"] = label
    del model["display_categories"]
