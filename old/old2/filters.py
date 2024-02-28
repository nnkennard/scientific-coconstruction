import editdistance
import re


class Categories(object):
    NUMERIC = "numeric"
    TYPO = "typo"
    OTHER = "other"
    LONG_ADDITION = "long_addition"
    LONG_DELETION = "long_deletion"
    CITATION_ADDED = "citation_added"
    WORD_SWAP = "word_swap"
    INVALID = "invalid"
    PHRASE_INSERTED = "phrase_inserted"
    REPHRASE = "rephrase"


def diff_total_len(diff):
    diff_len = 0
    if diff['old'] is not None:
        diff_len += len(diff['old'])
    if diff['new'] is not None:
        diff_len += len(diff['new'])
    assert not diff_len == 0
    return diff_len


def diff_abs_len(diff):
    diff_len = 0
    if diff['old'] is not None:
        diff_len -= len(diff['old'])
    if diff['new'] is not None:
        diff_len += len(diff['new'])
    return diff_len


def all_tokens(diff):
    tokens = []
    if diff['old'] is not None:
        tokens += diff['old']
    if diff['new'] is not None:
        tokens += diff['new']
    return tokens


def alphabetical(diff):
    long_string = "".join(all_tokens(diff))
    return len([x
                for x in long_string if x.isalpha()]) / len(long_string) > 0.8


def numeric(diff):
    long_string = "".join(all_tokens(diff))
    return len([x for x in long_string if x.isnumeric()
                ]) / len(long_string) > 0.5


def citation_added(diff):
    if diff['new'] is None or diff_abs_len(diff) > 15:
        return False
    else:
        return re.search('[0-9]{4}\)', "".join(diff['new'])) is not None

def word_swap(diff):
    old, new = un_none(diff)
    return len(old) == 1 and len(new) == 1

def rephrase(diff): # Needs lemmatization
    old, new = un_none(diff)
    return len(set(old).intersection(new)) > 0


def un_none(diff):
    return ([] if diff['old'] is None else diff['old'],
            [] if diff['new'] is None else diff['new'])

def invalid_additions(diff):
    return (diff['old'] is not None and diff['old'][:2] == ['Anonymous', 'authors']
            or diff['new'] is not None and diff['new'][0] == 'ACKNOWLEDGEMENTS'
            or  'github' in "".join(un_none(diff)[1]))

def edit_distance(diff):
    old, new = un_none(diff)
    return editdistance.eval("".join(old), "".join(new))

def phrase_inserted(diff):
    old, new = un_none(diff)
    return (not old) and (not any(c.isdigit() for c in "".join(new)))
