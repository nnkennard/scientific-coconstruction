import json
import sys

import openreview_lib as orl
from diff_lib import Diff

def maybe_len(maybe_text):
    return len(maybe_tokens(maybe_text))

def maybe_tokens(maybe_text):
    if maybe_text is None:
        return []
    else:
        return maybe_text
def main():

    with open(sys.argv[1], 'r') as f:
        obj = json.load(f)
        curr_location = -1
        current_merge_set = []
        flat_original_tokens = sum(obj['tokens'][orl.EventType.PRE_REBUTTAL_REVISION], [])
        final_diffs = []
        for i, d in enumerate(obj['diffs']):
            if d['location'] - curr_location < 10 and curr_location > 0:
                if current_merge_set:
                    current_merge_set.append(i)
                else:
                    current_merge_set += [i-1, i]
            else:
                if current_merge_set:
                    old_tokens = []
                    new_tokens = []
                    prev_trailing_index = 0

                    for diff_idx in current_merge_set:
                        diff = obj['diffs'][diff_idx]
                        if prev_trailing_index:
                            trailing_tokens = flat_original_tokens[prev_trailing_index:diff['location']+1]
                            old_tokens += trailing_tokens
                            new_tokens += trailing_tokens
                        old_tokens += maybe_tokens(diff['old'])
                        new_tokens += maybe_tokens(diff['new'])

                        prev_trailing_index = diff['location'] + maybe_len(diff['old'])

                    location = obj['diffs'][current_merge_set[0]]['location']
                    if not old_tokens:
                        old_tokens = None
                    if not new_tokens:
                        new_tokens = None
                    new_diff = Diff(location, old_tokens, new_tokens)
                    print("+++ Replaced")
                    for i in current_merge_set:
                        print(obj['diffs'][i])
                    print("=== With")
                    print(new_diff)
                    current_merge_set = []
                    print()
            curr_location = d['location'] + maybe_len(d['old'])


if __name__ == "__main__":
    main()