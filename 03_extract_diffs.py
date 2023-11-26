import argparse
import glob
import json
import os
import stanza
import tqdm

import scc_lib
from diff_lib import make_diffs

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")


def read_sentencized(filename):
    with open(filename, "r") as f:
        return [line.split() for line in f.readlines()]


def get_versions(discussion_obj):
    versions = {}
    for a, b, c in discussion_obj["versions"]:
        if b is None or c is None:
            assert b is None and c is None
        else:
            versions[a] = read_sentencized(b.replace("pdf", "txt"))
    return versions


def get_tokens(filename):
    with open(filename, 'r') as f:
        text = f.read()
        return list([
            t['text'] for s in scc_lib.SENTENCIZE_PIPELINE(text).to_dict()
            for t in s
        ])


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
