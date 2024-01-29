import collections
import json
import sys


def build_sentence_map(sentences):
    sentence_index_map = []
    for i, sentence in enumerate(sentences):
        sentence_index_map += [i] * len(sentence)
    return sentence_index_map


def get_all_tokens(diff):
    old = diff['old']
    if old is None:
        old = []
    new = diff['new']
    if new is None:
        new = []
    return old, new


def main():

    diff_file = sys.argv[1]
    with open(diff_file, 'r') as f:
        obj = json.load(f)

        flat_initial_tokens = sum(obj['tokens']['initial'], [])
        sentence_index_map = build_sentence_map(obj['tokens']['initial'])

        print(len(obj['diffs']))
        print()
        sentencewise_collector = collections.defaultdict(list)
        for diff in obj['diffs']:
            sent_index = sentence_index_map[diff['location']]
            sentencewise_collector[sent_index].append(diff)

    new_diffs = []
    for sentence_index in sorted(sentencewise_collector.keys()):
        this_sentence_diffs = sentencewise_collector[sentence_index]

        if len(this_sentence_diffs) == 1:
            new_diffs += this_sentence_diffs
            continue

        # Multiple diffs in this sentence
        merged_old = []
        merged_new = []

        for i, d in enumerate(this_sentence_diffs):
            old, new = get_all_tokens(d)
            merged_old += old
            merged_new += new

            if i == len(this_sentence_diffs) - 1:  # this is the last one
                break

            # find the in between part and add to both
            end_location_of_current_diff = d['location'] + len(old)
            old_location_of_next_diff = this_sentence_diffs[i + 1]['location']
            in_between_part = flat_initial_tokens[
                end_location_of_current_diff:old_location_of_next_diff]
            merged_old += in_between_part
            merged_new += in_between_part
        new_diffs.append({
            "location": this_sentence_diffs[0]['location'],
            'old': merged_old,
            'new': merged_new
        })

    print(len(new_diffs))
    final_diffs_obj = {'tokens': obj['tokens'], 'diffs': new_diffs}

    with open('final_diffs.json', 'w') as f:
        json.dump(final_diffs_obj, f)


if __name__ == "__main__":
    main()
