import argparse
import glob
import json
import tqdm

import openreview_lib as orl
from diff_lib import make_diffs

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")
parser.add_argument("-c", "--conference", default="", type=str, help="")


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


def main():
    args = parser.parse_args()
    for filename in tqdm.tqdm(
        list(glob.glob(f"{args.data_dir}/{args.conference}/*/discussion.json"))
    ):

        with open(filename, "r") as f:
            versions = get_versions(json.load(f))
            if (
                orl.EventType.PRE_REBUTTAL_REVISION not in versions
                or orl.EventType.FINAL_REVISION not in versions
            ):
                continue
            else:
                diffs = make_diffs(
                    versions[orl.EventType.PRE_REBUTTAL_REVISION],
                    versions[orl.EventType.FINAL_REVISION],
                )
                with open(
                    filename.replace("discussion", "diffs").replace(".json",
                    ".json"),
                    "w",
                ) as g:
                  json.dump(diffs, g)


if __name__ == "__main__":
    main()
