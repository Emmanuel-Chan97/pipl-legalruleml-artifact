"""Map the former question envelopes to their fields in the first-round storage view."""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json


QUESTIONS_BY_FIELD = {
    "participants": "who_is_involved",
    "content_expr": "what_action",
    "conduct_force": "what_force",
    "activation": "what_triggers_it",
    "exceptions": "what_exceptions",
    "temporal": "when",
    "applicability": "what_scope",
    "effects": "what_effects",
}
FORCE_ELEMENTS = {"lrml:Obligation", "lrml:Permission", "lrml:Prohibition"}
FIELDS_BY_QUESTION = {question: field for field, question in QUESTIONS_BY_FIELD.items()}
FIELDS_BY_QUESTION["does_conduct_force_apply"] = "conduct_force"
QUESTION_NAMES = FIELDS_BY_QUESTION.keys()
ABSENT = object()


def _question_name(record, field):
    if field == "conduct_force" and record["legalruleml"].get("native_element") not in FORCE_ELEMENTS:
        return "does_conduct_force_apply"
    return QUESTIONS_BY_FIELD[field]


def _targets_by_record(model):
    """Read exception membership and target independently, respecting their original order."""
    targets = defaultdict(list)
    for exception in model["exceptions"]:
        for record_id in exception["record_refs"]:
            values = targets[record_id]
            for target in exception["target_ids"]:
                if target not in values:
                    values.append(target)
    return targets


def _identity(anchor):
    if not isinstance(anchor, dict):
        raise ValueError("Expected a source anchor object")
    return json.dumps(anchor, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _anchor_ref(catalog, anchor):
    # The hash seeds an ID during migration. Existing R2 keys continue to work after editing their object.
    key = "a-" + sha256(_identity(anchor).encode("utf-8")).hexdigest()[:20]
    if key in catalog and catalog[key] != anchor:
        raise ValueError(f"Source anchor identifier collision: {key}")
    if key not in catalog:
        catalog[key] = deepcopy(anchor)
    return key


def _store_answer(original, field, record, targets, catalog):
    reserved = {"anchor_refs", "target_record_ids_override"}
    if reserved.intersection(original):
        raise ValueError(f"Compact annotation fields already present at {record['id']}.{field}")
    answer = deepcopy(original)
    anchors = answer.pop("source_anchors")
    if not isinstance(anchors, list):
        raise ValueError(f"Expected an ordered anchor array at {record['id']}.{field}")
    if anchors:
        answer["anchor_refs"] = [_anchor_ref(catalog, anchor) for anchor in anchors]
    if not anchors and "answer_state" in answer and answer["coverage"] == answer["answer_state"]:
        del answer["coverage"]

    if field == "conduct_force":
        if answer["note"] == record["linguistic_form"]["scope_note"]:
            del answer["note"]
    if field == "exceptions":
        supplied = answer.pop("target_record_ids", ABSENT)
        derived = targets if targets else ABSENT
        if supplied != derived:
            # null explicitly means the old assessment omitted this key despite linked exceptions.
            if supplied is not ABSENT and not isinstance(supplied, list):
                raise ValueError(f"Expected an array of target record IDs at {record['id']}.{field}")
            answer["target_record_ids_override"] = None if supplied is ABSENT else supplied
    return answer


def _restore_answer(stored, field, record, targets, catalog):
    if "source_anchors" in stored or (field == "exceptions" and "target_record_ids" in stored):
        raise ValueError(f"Duplicate expanded annotation field at {record['id']}.{field}")
    answer = deepcopy(stored)
    refs = answer.pop("anchor_refs", [])
    if not isinstance(refs, list):
        raise ValueError(f"Expected an ordered list of anchor references at {record['id']}.{field}")
    try:
        answer["source_anchors"] = [deepcopy(catalog[ref]) for ref in refs]
    except KeyError as error:
        raise ValueError(f"Unknown anchor {error.args[0]} at {record['id']}.{field}") from error
    if "coverage" not in answer:
        if refs or "answer_state" not in answer:
            raise ValueError(f"Missing independent coverage at {record['id']}.{field}")
        answer["coverage"] = answer["answer_state"]
    if field == "conduct_force":
        answer.setdefault("note", record["linguistic_form"]["scope_note"])
    if field == "exceptions":
        value = answer.pop("target_record_ids_override", targets or None)
        if value is not None:
            if not isinstance(value, list):
                raise ValueError(f"Expected an array of target record IDs at {record['id']}.{field}")
            answer["target_record_ids"] = list(value)
    return answer


def compact(model):
    """Replace the eight per-record question objects; consume a first-round storage model."""
    if "source_anchor_catalog" in model:
        raise ValueError("The source anchor catalog already exists")
    prompts = model["question_catalog"]
    if prompts.keys() != QUESTION_NAMES or any("annotation_slot" in prompt for prompt in prompts.values()):
        raise ValueError("Unexpected or already migrated question catalog")
    targets = _targets_by_record(model)
    catalog = {}
    prepared = []
    for record in model["records"]:
        expected = {_question_name(record, field) for field in QUESTIONS_BY_FIELD}
        if "field_annotations" in record or (QUESTION_NAMES & record.keys()) != expected:
            raise ValueError(f"Unexpected questions for record {record['id']} and its declared native element")
        fields = {}
        for field in QUESTIONS_BY_FIELD:
            original = record[_question_name(record, field)]
            fields[field] = _store_answer(original, field, record, targets[record["id"]], catalog)
        prepared.append((record, expected, fields))

    for question, prompt in prompts.items():
        prompt["annotation_slot"] = FIELDS_BY_QUESTION[question]
    model["source_anchor_catalog"] = catalog
    for record, names, fields in prepared:
        for key in names:
            del record[key]
        record["field_annotations"] = fields


def expand(model):
    """Restore the first-round storage model, including the original ordered field provenance."""
    prompts = model["question_catalog"]
    if prompts.keys() != QUESTION_NAMES or any(
        prompt.get("annotation_slot") != FIELDS_BY_QUESTION[q] for q, prompt in prompts.items()
    ):
        raise ValueError("The question catalog has a missing or incorrect annotation slot")
    targets = _targets_by_record(model)
    catalog = model["source_anchor_catalog"]
    seen = set()
    for anchor in catalog.values():
        identity = _identity(anchor)
        if identity in seen:
            raise ValueError("Duplicate complete anchor objects in source_anchor_catalog")
        seen.add(identity)
    prepared = []
    for record in model["records"]:
        annotations = record["field_annotations"]
        if (QUESTION_NAMES & record.keys()) or annotations.keys() != QUESTIONS_BY_FIELD.keys():
            raise ValueError(f"Unexpected or duplicate field annotations on {record['id']}")
        restored = {}
        for field, answer in annotations.items():
            question = _question_name(record, field)
            restored[question] = _restore_answer(answer, field, record, targets[record["id"]], catalog)
        prepared.append((record, restored))

    for prompt in prompts.values():
        del prompt["annotation_slot"]
    del model["source_anchor_catalog"]
    for record, restored in prepared:
        del record["field_annotations"]
        record.update(restored)
