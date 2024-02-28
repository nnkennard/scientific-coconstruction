import argparse
import collections
import glob
import json

from filters import *

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")


def count_diffs(obj, identifier):
    mini_counter = collections.defaultdict(list)
    for pdiff in obj['diffs']:
        diff = (identifier, pdiff)
        if pdiff['old'] is None:
            print(diff)
        continue
        if numeric(pdiff):
            mini_counter[Categories.NUMERIC].append(diff)
        elif diff_total_len(pdiff) < 5 and edit_distance(pdiff) < 3:
            mini_counter[Categories.TYPO].append(diff)
        elif word_swap(pdiff):
            mini_counter[Categories.WORD_SWAP].append(diff)
        elif diff_abs_len(pdiff) > 100:
            mini_counter[Categories.LONG_ADDITION].append(diff)
        elif diff_abs_len(pdiff) < -100:
            mini_counter[Categories.LONG_DELETION].append(diff)
        elif citation_added(pdiff):
            mini_counter[Categories.CITATION_ADDED].append(diff)
        elif rephrase(pdiff):
            mini_counter[Categories.REPHRASE].append(diff)
        elif invalid_additions(pdiff):
            mini_counter[Categories.INVALID].append(diff)
        elif phrase_inserted(pdiff):
            mini_counter[Categories.PHRASE_INSERTED].append(diff)
        else:
            mini_counter[Categories.OTHER].append(diff)
    return {}
    return mini_counter


def build_sentence_lookup(sentences):
    lookup = []
    for sent_i, sentence in enumerate(sentences):
        for token in sentence:
            lookup.append(sent_i)
    return lookup


def print_contextualized(diff, initial_tokens, sentence_lookup):
    old, new = un_none(diff)
    diff_start_sentence = sentence_lookup[diff['location']]
    try:
        diff_end_sentence = sentence_lookup[diff['location'] + len(new) - len(old) -1 ]
        if diff_start_sentence == diff_end_sentence:
            print(" ".join(initial_tokens[diff_start_sentence]))
    except:
        pass

def main():
    args = parser.parse_args()
    diff_counter = collections.defaultdict(list)
    insert_diffs = []
    for filename in glob.glob(f'{args.data_dir}/*/diffs.json'):
        with open(filename, 'r') as f:
            obj = json.load(f)
            identifier = filename.split("/")[-2]
            for diff in obj['diffs']:
                if diff['old'] is None:
                    insert_diffs.append(diff)

    for d in sorted(insert_diffs, key=lambda x: len(x['new'])):
        print(d)

if __name__ == "__main__":
    main()
