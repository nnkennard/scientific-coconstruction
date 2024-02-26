import json
import sys

def get_len(tokens):
    if tokens is None:
        return 0
    else:
        return len(tokens)

MAX_INTER_DIFF = 6

def main():

    diff_dir = sys.argv[1]

    new_diffs = {}

    with open(f'{diff_dir}/diffs.json', 'r') as f:
        obj = json.load(f)
        new_diffs['tokens'] = obj['tokens']
        old_diffs = obj['diffs']

        curr_diff_i = 0
        diffs_to_merge_with_prev = []

        for i, curr_diff in enumerate(old_diffs[:-1]):
            next_diff = old_diffs[i+1]

            curr_diff_start = curr_diff['location']
            curr_diff_end = curr_diff_start + get_len(curr_diff['old'])

            

            if next_diff['location'] - curr_diff_end < MAX_INTER_DIFF:
                print("=" * 80)
                print(i+1)
                print()
                print(curr_diff)
                print(next_diff)
                print(next_diff['location'], curr_diff_start, curr_diff_end)
                print(">", next_diff['location'] - curr_diff_end)
                diffs_to_merge_with_prev.append(i+1)
 

if __name__ == "__main__":
  main()

