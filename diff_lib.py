import collections
import difflib
import myers
import re
import openreview_lib as orl


VERSIONS = [orl.EventType.PRE_REBUTTAL_REVISION, orl.EventType.FINAL_REVISION]
FIRST, LAST = VERSIONS

Diff = collections.namedtuple("Diff", "location old new", defaults=(None, None, None))
NonMatchingBlock = collections.namedtuple("NonMatchingBlock", "a, b, a_len, b_len")


def check_reconstruction(first_tokens, last_tokens, diff_map):
    constructed_final_tokens = []

    i = 0
    while i < len(first_tokens):
        if i not in diff_map:
            constructed_final_tokens.append(first_tokens[i])
            i += 1
        else:
            diff = diff_map[i]
            if diff.old is None:
                constructed_final_tokens.append(first_tokens[i])
                i += 1
            else:
                i += len(diff.old)
            if diff.new is not None:
                constructed_final_tokens += list(diff.new)

    return constructed_final_tokens == last_tokens


def get_simple_diffs(first_tokens, last_tokens, min_len=5):
    matching_blocks = difflib.SequenceMatcher(
        None, first_tokens, last_tokens
    ).get_matching_blocks()
    if matching_blocks[0][0] == 0 and matching_blocks[0][1] == 0:
        pass
    else:
        matching_blocks = [(0, 0, 0)] + matching_blocks

    non_matching_blocks = []
    last_a_index = 0
    last_b_index = 0
    for a, b, size in matching_blocks:
        if size < min_len:
            continue
        non_matching_block = NonMatchingBlock(
            last_a_index, last_b_index, a - last_a_index, b - last_b_index
        )
        non_matching_blocks.append(non_matching_block)
        last_a_index = a + size
        last_b_index = b + size

    if len(first_tokens) > last_a_index or len(last_tokens) > last_b_index:
        non_matching_blocks.append(
            NonMatchingBlock(
                last_a_index,
                last_b_index,
                len(first_tokens) - last_a_index,
                len(last_tokens) - last_b_index,
            )
        )

    diff_map = {}
    for block in sorted(non_matching_blocks):
        print(block.a_len, block.b_len)
        mini_first = first_tokens[block.a : block.a + block.a_len]
        mini_last = last_tokens[block.b : block.b + block.b_len]
        if abs(block.b_len - block.a_len) > 2000:
            deleted_tokens = mini_first
            added_tokens = mini_last
            diff_map[block.a] = Diff(
                location=block.a,
                old=(tuple(deleted_tokens) if deleted_tokens else None),
                new=(tuple(added_tokens) if added_tokens else None),
            )
            continue

        myers_diff = myers.diff(mini_first, mini_last)
        first_file_indices = []
        current_first_file_index = -1
        for action, token in myers_diff:
            if action in "kr":
                current_first_file_index += 1
            first_file_indices.append(current_first_file_index)

        action_string = "".join(x[0] for x in myers_diff)
        for match in re.finditer("[ir]+", action_string):
            assert re.match("^r*i*$|^i*r*$", match.group()) is not None
            tokens_added = []
            tokens_deleted = []
            start, end = match.start(), match.end()
            for action, token in myers_diff[start:end]:
                if action == "i":
                    tokens_added.append(token)
                else:
                    tokens_deleted.append(token)
            location = block.a + first_file_indices[start]
            diff_map[location] = Diff(
                location=location,
                old=(tuple(tokens_deleted) if tokens_deleted else None),
                new=(tuple(tokens_added) if tokens_added else None),
            )

    if not check_reconstruction(first_tokens, last_tokens, diff_map):
        print("Diff error")
        return None

    return diff_map


def make_diffs(first_tokens_sentencized, last_tokens_sentencized, check=True):
    first_tokens = sum(first_tokens_sentencized, [])
    last_tokens = sum(last_tokens_sentencized, [])
    if first_tokens == last_tokens:
        return

    diff_map = get_simple_diffs(first_tokens, last_tokens)
    if diff_map is None:
        return None

    return {
        "tokens": {FIRST: first_tokens_sentencized, LAST: last_tokens_sentencized},
        "diffs": sorted(
            [d._asdict() for d in diff_map.values()], key=lambda x: x["location"]
        ),
    }
