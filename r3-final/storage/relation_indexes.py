"""Canonical sources are records[].effects and legal_relations[].record_ids."""

from copy import deepcopy


def _derive_indexes(model):
    records = model["records"]
    position_refs = {record["id"]: [] for record in records}
    if len(position_refs) != len(records):
        raise ValueError("Duplicate record ID in records")

    relation_ids = set()
    for relation in model["legal_relations"]:
        relation_id = relation["id"]
        if relation_id in relation_ids:
            raise ValueError(f"Duplicate legal relation ID: {relation_id}")
        relation_ids.add(relation_id)
        members = relation["record_ids"]
        if len(members) != len(set(members)):
            raise ValueError(f"Duplicate member of legal relation {relation_id}")
        for member in members:
            if member not in position_refs:
                raise ValueError(f"Unknown record {member} in legal relation {relation_id}")
            position_refs[member].append(relation_id)

    effects = []
    for record in records:
        source = record["id"]
        for number, effect in enumerate(record["effects"], start=1):
            if "id" in effect or "source_record" in effect:
                raise ValueError(f"Generated effect index fields on {source}, effect {number}")
            for target in effect["target_ids"]:
                if target not in position_refs:
                    raise ValueError(f"Unknown effect target {target} in record {source}")
            entry = deepcopy(effect)
            entry["id"] = f"effect-{source}-{number}"
            entry["source_record"] = source
            effects.append(entry)
    return position_refs, effects


def compact(model):
    """Check all projections before removing the redundant copies in place."""
    position_refs, effects = _derive_indexes(model)
    if model["effect_templates"] != effects:
        raise ValueError("effect_templates disagrees with the ordered effects in records")
    for record in model["records"]:
        if record["legal_position_refs"] != position_refs[record["id"]]:
            raise ValueError(f"Legal position references disagree for record {record['id']}")
    del model["effect_templates"]
    for record in model["records"]:
        del record["legal_position_refs"]


def expand(model):
    """Rebuild both legacy indexes in their original list order in place."""
    if "effect_templates" in model or any("legal_position_refs" in r for r in model["records"]):
        raise ValueError("A generated effect or legal position index is already present")
    position_refs, effects = _derive_indexes(model)
    model["effect_templates"] = effects
    for record in model["records"]:
        record["legal_position_refs"] = position_refs[record["id"]]
