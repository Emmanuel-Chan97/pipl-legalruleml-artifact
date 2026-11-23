"""Store common editorial notes, review statuses and issue texts once."""
from collections import Counter


def _group_notes(records, get_note):
    values = [get_note(record) for record in records]
    if not all(isinstance(value, str) for value in values):
        raise ValueError("Editorial notes must be text")
    counts = Counter(values)
    default = counts.most_common(1)[0][0]
    overrides = {}
    for record, text in zip(records, values):
        if text != default:
            overrides.setdefault(text, []).append(record['id'])
    return {
        'default': default,
        'overrides': [
            {'text': text, 'record_ids': ids}
            for text, ids in overrides.items()
        ],
    }


def _notes_by_record(group, record_ids):
    by_record = {}
    for entry in group['overrides']:
        for record_id in entry['record_ids']:
            if record_id not in record_ids or record_id in by_record:
                raise ValueError(f'Unknown or repeated editorial note assignment: {record_id}')
            by_record[record_id] = entry['text']
    return {key: by_record.get(key, group['default']) for key in record_ids}


def compact(model):
    records = model['records']
    if 'editorial_defaults' in model:
        raise ValueError('Model already contains compact editorial defaults')
    if not records:
        return
    record_ids = {record['id'] for record in records}
    if len(record_ids) != len(records):
        raise ValueError('Editorial note assignments require unique record IDs')
    default_status = model['review_status']
    groups = {
        'representation_note': _group_notes(records, lambda r: r['representation_note']),
        'review_note': _group_notes(records, lambda r: r['review']['note']),
        'issue_texts': {},
    }
    issue_ids = {}
    for record in records:
        review = record['review']
        if 'issue_refs' in review or not isinstance(review['issues'], list):
            raise ValueError(f"Invalid legacy review in record {record['id']}")
        review.pop('note')
        record.pop('representation_note')
        if review['status'] == default_status:
            review.pop('status')
        refs = []
        for issue in review.pop('issues'):
            if not isinstance(issue, str):
                raise ValueError(f"Review issue in record {record['id']} must be text")
            if issue not in issue_ids:
                ref = f'issue-{len(issue_ids) + 1:03d}'
                issue_ids[issue] = ref
                groups['issue_texts'][ref] = issue
            refs.append(issue_ids[issue])
        if refs:
            review['issue_refs'] = refs
        if not review:
            record.pop('review')
    model['editorial_defaults'] = groups


def expand(model):
    records = model['records']
    if not records and 'editorial_defaults' not in model:
        return
    groups = model['editorial_defaults']
    record_ids = {record['id'] for record in records}
    if len(record_ids) != len(records):
        raise ValueError('Editorial note assignments require unique record IDs')
    representations = _notes_by_record(groups['representation_note'], record_ids)
    review_notes = _notes_by_record(groups['review_note'], record_ids)
    issue_texts = groups['issue_texts']
    for record in records:
        record_id = record['id']
        review = record.setdefault('review', {})
        if 'representation_note' in record or 'note' in review or 'issues' in review:
            raise ValueError(f'Duplicate compact and expanded editorial fields in {record_id}')
        review.setdefault('status', model['review_status'])
        refs = review.pop('issue_refs', [])
        unknown = [ref for ref in refs if ref not in issue_texts]
        if unknown:
            raise ValueError(f'Unknown issue reference in {record_id}: {unknown}')
        review['issues'] = [issue_texts[ref] for ref in refs]
        review['note'] = review_notes[record_id]
        record['representation_note'] = representations[record_id]
    model.pop('editorial_defaults')
