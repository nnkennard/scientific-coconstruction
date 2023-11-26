import argparse
import glob
import json
import sys

from diff_lib import Diff

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")

MAX_DIST = 10


def maybe_len(maybe_text):
    return len(maybe_tokens(maybe_text))


def maybe_tokens(maybe_text):
    if maybe_text is None:
        return []
    else:
        return maybe_text


# {'location': 1644, 'old': ['Under', 'review'], 'new': ['Published']}
def is_header(diff):
    if diff['old'] == ['Under', 'review'] and diff['new'] == ['Published']:
        print('x')
        return True
    elif diff['new'] is not None and 'Published' in diff['new']:
        print("****", diff)
    return False


def clean_diffs(filename):
    with open(filename, 'r') as f:
        obj = json.load(f)

    curr_location = -1
    curr_merge_set = None
    orig_tokens = obj['tokens']['initial']
    final_diffs = []

    for i, d in enumerate(obj['diffs']):
        if is_header(d):
            continue
        if d['location'] - curr_location < MAX_DIST and curr_location > 0:
            if curr_merge_set is not None:
                curr_merge_set.append(i)  # Add this one in too
            else:
                curr_merge_set = [i - 1, i]  # Start the merge set
        else:  # We are a sufficient distance away
            if curr_merge_set:  # And we just passed some things that need to be merged
                old_tokens = []  # The whole 'old' part of the merged diff
                new_tokens = []  # The whole 'new' part of the merged diff
                prev_trailing_index = 0  # To find the tokens in between the two diffs to be merged

                for diff_idx in curr_merge_set:
                    diff = obj['diffs'][diff_idx]
                    if prev_trailing_index:
                        trailing_tokens = orig_tokens[
                            prev_trailing_index:diff['location'] + 1]
                        # TODO: ^ why is this +1???
                        old_tokens += trailing_tokens
                        new_tokens += trailing_tokens
                    old_tokens += maybe_tokens(diff['old'])
                    new_tokens += maybe_tokens(diff['new'])

                    prev_trailing_index = diff['location'] + maybe_len(
                        diff['old'])

                location = obj['diffs'][curr_merge_set[0]]['location']
                # Merged diff starts at the location of the first diff added to
                # the merge set
                if not old_tokens:
                    old_tokens = None
                if not new_tokens:
                    new_tokens = None
                new_diff = Diff(location, old_tokens, new_tokens)
                print("+++ Replaced")
                for i in curr_merge_set:
                    print(obj['diffs'][i])
                print("=== With")
                print(new_diff)
                curr_merge_set = None
                print()
        curr_location = d['location'] + maybe_len(d['old'])


def main():

    args = parser.parse_args()
    for filename in glob.glob(f'{args.data_dir}/*/diffs.json')[:10]:
        clean_obj = clean_diffs(filename)
        clean_file = filename.replace('diffs.json', 'clean_diffs.json')
        with open(clean_file, 'w') as f:
            f.write(clean_file)


if __name__ == "__main__":
    main()
