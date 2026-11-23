"""Convert among the round-two, round-one and fully expanded PIPL formats."""
from copy import deepcopy

from . import questions, round_one

STORAGE_PROFILE = 'pipl-field-annotations-r2'


def to_round_one(source):
    profile = source.get('storage_profile')
    if profile == STORAGE_PROFILE:
        model = deepcopy(source)
        questions.expand(model)
        model['storage_profile'] = round_one.STORAGE_PROFILE
        return model
    if profile == round_one.STORAGE_PROFILE:
        return deepcopy(source)
    return round_one.compact(source)


def compact(source):
    """Create the editable R2 representation from an R1 or earlier expanded file."""
    if source.get('storage_profile') == STORAGE_PROFILE:
        raise ValueError('This file is already in the round-two format')
    model = to_round_one(source)
    questions.compact(model)
    model['storage_profile'] = STORAGE_PROFILE
    return model


def expand(source):
    """Produce the full v4.1 role/label record view for existing readers."""
    if source.get('storage_profile') == round_one.STORAGE_PROFILE:
        return round_one.expand(source)
    return round_one.expand(to_round_one(source))


def for_export(source):
    return expand(source) if 'storage_profile' in source else source
