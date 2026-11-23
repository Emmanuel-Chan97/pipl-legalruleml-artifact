"""Share primary-source fragments and exception definitions in the PIPL model."""
from collections import defaultdict
from copy import deepcopy


def _index(rows, label):
    result = {}
    for row in rows:
        identifier = row["id"]
        if identifier in result:
            raise ValueError(f"Duplicate {label} ID: {identifier}")
        result[identifier] = row
    return result


def _exception_membership(model):
    # Attachments preserve an editorial relationship. Targets encode legal effect.
    records = _index(model["records"], "record")
    membership = defaultdict(list)
    for exc in _index(model["exceptions"], "exception").values():
        for field in ("record_refs", "target_ids"):
            seen = set()
            for record_id in exc[field]:
                if record_id not in records or record_id in seen:
                    raise ValueError(f"{exc['id']}.{field}: invalid record ID {record_id!r}")
                seen.add(record_id)
                if field == "record_refs":
                    membership[record_id].append(exc)
    return membership


def _read_fragment(fragments, sources, record, fragment_id):
    fragment = fragments.get(fragment_id)
    if fragment is None:
        raise ValueError(f"{record['id']}: unknown source fragment {fragment_id!r}")
    source = sources.get(fragment["full_context_ref"])
    if source is None or source["article"] != fragment["article"] or record.get("article", fragment["article"]) != fragment["article"]:
        raise ValueError(f"{record['id']}: inconsistent article or source for {fragment_id!r}")
    ref = {
        "fragment_id": fragment_id,
        "article_ref": f"a{source['article']}",
        "document_version": f"PIPL-{source['version']}",
        "citation": record["citation"],
        "url": source["url"],
    }
    return fragment["quote"], ref


def compact(model):
    """Replace record-level quotations/references and remove duplicate exception objects."""
    fragments = _index(model["source_fragments"], "fragment")
    sources = _index(model["sources"], "source")
    membership = _exception_membership(model)
    # Refuse a lossy migration before changing anything in this module.
    for record in model["records"]:
        refs = record["source_refs"]
        if len(refs) != 1 or "source_fragment_id" in record:
            raise ValueError(f"{record['id']}: expected exactly one original source reference")
        quote, ref = _read_fragment(fragments, sources, record, refs[0]["fragment_id"])
        if record["source_quote"] != quote or refs[0] != ref:
            raise ValueError(f"{record['id']}: source fields contain independent information")
        if record["exceptions"] != membership[record["id"]]:
            raise ValueError(f"{record['id']}: exception content, membership or order differs")
    for record in model["records"]:
        record["source_fragment_id"] = record.pop("source_refs")[0]["fragment_id"]
        del record["article"], record["source_quote"], record["exceptions"]


def expand(model):
    """Build the compatibility view from authoritative catalogs and record citations."""
    fragments = _index(model["source_fragments"], "fragment")
    sources = _index(model["sources"], "source")
    membership = _exception_membership(model)
    prepared = []
    for record in model["records"]:
        for derived_key in ("article", "source_quote", "source_refs", "exceptions"):
            if derived_key in record:
                raise ValueError(f"{record['id']}: remove duplicate derived key {derived_key!r}")
        quote, ref = _read_fragment(fragments, sources, record, record["source_fragment_id"])
        prepared.append((record, quote, ref, membership[record["id"]]))
    for record, quote, ref, exceptions in prepared:
        record["article"] = fragments[record.pop("source_fragment_id")]["article"]
        record["source_quote"] = quote
        record["source_refs"] = [ref]
        record["exceptions"] = deepcopy(exceptions)
