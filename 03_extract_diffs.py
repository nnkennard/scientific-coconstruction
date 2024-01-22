import argparse
import glob
import json
import os
import tqdm

import scc_lib
from diff_lib import make_diffs

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")


def read_sentencized(filename):
    with open(filename, "r") as f:
        return [line.split() for line in f.readlines()]


def get_tokens(filename):
    with open(filename, 'r') as f:
        text = f.read()
        return list([t.to_dict()[0]['text'] for t in s.tokens]
                    for s in scc_lib.SENTENCIZE_PIPELINE(text).sentences)


def main():
    args = parser.parse_args()
    for initial_filename in tqdm.tqdm(
            list(glob.glob(f"{args.data_dir}/*/initial.txt"))):
        if not os.path.isfile(f'{initial_filename[:-11]}diffs.json'):
            final_filename = f'{initial_filename[:-11]}final.txt'
            diffs = make_diffs(get_tokens(initial_filename),
                               get_tokens(final_filename))
            with open(f'{initial_filename[:-11]}diffs.json', 'w') as f:
                f.write(json.dumps(diffs, indent=2))


if __name__ == "__main__":
    main()
