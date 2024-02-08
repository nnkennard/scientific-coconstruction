import argparse
import collections
import glob
import json
import os
import sys
import tqdm

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")

def build_sentence_map(sentences):
    sentence_index_map = []
    for i, sentence in enumerate(sentences):
        sentence_index_map += [i] * len(sentence)
    sentence_index_map.append(sentence_index_map[-1] + 1)
    # Placeholder in case something is added at the end of the initial text
    # Shouldn't cause any problems, usually ignored
    return sentence_index_map


def get_all_tokens(diff):
    old = diff['old']
    if old is None:
        old = []
    new = diff['new']
    if new is None:
        new = []
    return old, new


def clean_diff(diff):
    if diff['old'] is None:
        diff['old'] = []
    if diff['new'] is None:
        diff['new'] = []
    return diff

def merge_diffs(original_diffs):
    flat_initial_tokens = sum(original_diffs['tokens']['initial'], [])
    if not flat_initial_tokens:
        return None
    sentence_index_map = build_sentence_map(original_diffs['tokens']['initial'])
    #print(len(flat_initial_tokens), len(sentence_index_map))
    sentencewise_collector = collections.defaultdict(list)
    for diff in original_diffs['diffs']:
        #print(diff['location'])
        sent_index = sentence_index_map[diff['location']]
        sentencewise_collector[sent_index].append(diff)

    new_diffs = []

    for sentence_index in sorted(sentencewise_collector.keys()):
        this_sentence_diffs = sentencewise_collector[sentence_index]

        if len(this_sentence_diffs) == 1: # nothing to merge
            only_diff, = this_sentence_diffs
            new_diffs.append(clean_diff(only_diff))
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

    return {'tokens': original_diffs['tokens'], 'diffs': new_diffs}



def main():

    args = parser.parse_args()

    for diff_dir in tqdm.tqdm(glob.glob(f'{args.data_dir}/*')):
        diff_file = f'{diff_dir}/diffs.json'
        merged_file = f'{diff_dir}/merged_diffs.json'

        # Only if merged diffs file doesn't exist
        if os.path.exists(merged_file):
            continue
        else:
            with open(diff_file, 'r') as f:
                obj = json.load(f)
            #print(diff_file)
            new_obj = merge_diffs(obj)
            if new_obj is not None:
                with open(f'{diff_dir}/merged_diffs.json', 'w') as f:
                    json.dump(new_obj, f)
            else:
                print("Error merging ", diff_file)

if __name__ == "__main__":
    main()
