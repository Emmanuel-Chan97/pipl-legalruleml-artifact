"""Current PIPL storage format and backwards-compatible projections."""
from copy import deepcopy
from . import classification, round_two

STORAGE_PROFILE = 'pipl-final-r3'


def to_round_two(source):
    profile = source.get('storage_profile')
    if profile == STORAGE_PROFILE:
        model = deepcopy(source)
        classification.expand(model)
        model['storage_profile'] = round_two.STORAGE_PROFILE
        return model
    if profile == round_two.STORAGE_PROFILE:
        return deepcopy(source)
    return round_two.compact(source)


def compact(source):
    if source.get('storage_profile') == STORAGE_PROFILE:
        raise ValueError('This file is already in the third-round format')
    model = to_round_two(source)
    classification.compact(model)
    model['storage_profile'] = STORAGE_PROFILE
    return model


def to_round_one(source):
    if source.get('storage_profile') == STORAGE_PROFILE:
        return round_two.to_round_one(to_round_two(source))
    return round_two.to_round_one(source)


def expand(source):
    if source.get('storage_profile') == STORAGE_PROFILE:
        return round_two.expand(to_round_two(source))
    return round_two.expand(source)


def for_export(source):
    return expand(source) if 'storage_profile' in source else source
