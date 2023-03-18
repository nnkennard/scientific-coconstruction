import collections
import glob
import json
import sys
import tqdm

import openreview_lib as orl


class DiffType(object):
    SingleToken = "single_token"
    Alpha = "alpha"
    NonAlpha = "non_alpha"
    Other = "other"


def convert_text(maybe_text):
    if maybe_text is None:
        return "NULL"
    else:
        return " ".join(maybe_text)


def is_single_token(diff):
    return (diff["old"] is None or len(diff["old"]) == 1) and (
        diff["new"] is None or len(diff["new"]) == 1
    )


def get_all_tokens(diff):
    if diff["old"] is None:
        old_text = []
    else:
        old_text = diff["old"]
    if diff["new"] is None:
        new_text = []
    else:
        new_text = diff["new"]
    return old_text, new_text


def get_all_text(diff):
    return [" ".join(x) for x in get_all_tokens(diff)]


def alpha_percent(diff):
    old_text, new_text = get_all_text(diff)
    alpha_count = non_alpha_count = 0
    for c in old_text + new_text:
        if c.isalpha() or c.isspace():
            alpha_count += 1
        else:
            non_alpha_count += 1
    alpha_count / (alpha_count + non_alpha_count)


CONTEXT_SIZE = 20


def main():
    for filename in list(glob.glob(f"{sys.argv[1]}/*/diffs.json")[:100]):
        forum = filename.split("/")[-2]
        with open(filename, "r") as g:
            obj = json.load(g)
            flat_initial_tokens = sum(
                obj["tokens"][orl.EventType.PRE_REBUTTAL_REVISION], []
            )
            if obj["diffs"] is not None and obj["diffs"]:
                for i, diff in enumerate(obj["diffs"]):
                    old_tokens, new_tokens = get_all_tokens(diff)
                    diff_start = diff["location"]
                    diff_end = diff_start + len(old_tokens)
                    start_window_size = max(0, diff_start - CONTEXT_SIZE)
                    print(
                        f"{forum} BC\t"
                        + " ".join(flat_initial_tokens[start_window_size:diff_start])
                    )
                    print(f"{forum} OL\t\t" + " ".join(old_tokens))
                    print(f"{forum} NW\t\t" + " ".join(new_tokens))
                    print(
                        f"{forum} CC\t"
                        + " ".join(
                            flat_initial_tokens[diff_end : diff_end + CONTEXT_SIZE]
                        )
                    )
                    print()


if __name__ == "__main__":
    main()
