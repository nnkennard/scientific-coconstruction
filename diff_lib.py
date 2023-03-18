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
    """Helper to apply diffs to original tokens and check against final tokens.
    Args:
        first_tokens: list of strings representing original tokens
        last_tokens: list of strings representing modified tokens
        diff_map: map from first_tokens index to Diff object.

    Returns:
        True if the diffs correctly map the changes, otherwise False.
    """
    constructed_final_tokens = []

    i = 0
    while i < len(first_tokens):
        if i not in diff_map:
            # No diff at this location
            constructed_final_tokens.append(first_tokens[i])
            i += 1
        else:
            diff = diff_map[i]
            if diff.old is None:
                # This is an insertion diff, insert after the token at this location
                constructed_final_tokens.append(first_tokens[i])
                i += 1
            else:
                # This is a deletion or modification diff. Skip some of first tokens
                i += len(diff.old)
            if diff.new is not None:
                # Insertion or modification diff. Add inserted tokens
                constructed_final_tokens += list(diff.new)

    return constructed_final_tokens == last_tokens


def get_simple_diffs(first_tokens, last_tokens, min_len=5):
    """TODO: write what this does.

    Args:
        first_tokens: list of strings representing original tokens
        last_tokens: list of strings representing modified tokens
        min_len: shortest matching block that shouldn't be subsumed
                 into neighboring nonmatching blocks


    """
    matching_blocks = difflib.SequenceMatcher(
        None, first_tokens, last_tokens
    ).get_matching_blocks()

    if matching_blocks[0][:2] != (0, 0):
        # The pair does not start with a matching block, add a placeholder
        matching_blocks = [(0, 0, 0)] + matching_blocks

    # Collect nonmatching blocks.
    non_matching_blocks = []
    last_a_index = 0
    last_b_index = 0
    for a, b, size in matching_blocks:
        if size >= min_len:
            # This matching block is large enough to delimit two separate nonmatching blocks
            non_matching_blocks.append(
                NonMatchingBlock(
                    last_a_index, last_b_index, a - last_a_index, b - last_b_index
                )
            )
            last_a_index = a + size
            last_b_index = b + size

    # In case the lists end in a nonmatching block
    if len(first_tokens) > last_a_index or len(last_tokens) > last_b_index:
        non_matching_blocks.append(
            NonMatchingBlock(
                last_a_index,
                last_b_index,
                len(first_tokens) - last_a_index,
                len(last_tokens) - last_b_index,
            )
        )

    # Map from indices in first_tokens to diffs at that index
    diff_map = {}
    for block in sorted(non_matching_blocks):
        mini_first = first_tokens[block.a : block.a + block.a_len]
        mini_last = last_tokens[block.b : block.b + block.b_len]
        if abs(block.b_len - block.a_len) > 2000:
            # This is a very large diff, it's not worth looking for characters within it
            # Just replace the whole original sequence with the whole final sequence
            deleted_tokens = mini_first
            added_tokens = mini_last
            diff_map[block.a] = Diff(
                location=block.a,
                old=(tuple(deleted_tokens) if deleted_tokens else None),
                new=(tuple(added_tokens) if added_tokens else None),
            )
            continue

        # Find maximal diffs in the nonmatching block
        myers_diff = myers.diff(mini_first, mini_last)

        # The result is a list of (action, line) pairs,
        # where action is one of KEEP, INSERT, REMOVE, or OMIT
        # (which happen to be the characters k, i, r, and o).
        # There is a line for each token in the first and last tokens lists
        # (same line, with a k, if the line is unchanged)

        first_file_indices = []
        # Which index in the first token list each Myers diff line is anchored to
        current_first_file_index = -1

        for action, token in myers_diff:
            if action in "kr":
                current_first_file_index += 1  # keep and remove advance by one index
            first_file_indices.append(current_first_file_index)

        action_string = "".join(x[0] for x in myers_diff)
        for match in re.finditer("[ir]+", action_string):
            # indices with a series of inserts and removes
            assert re.match("^r*i*$|^i*r*$", match.group()) is not None
            # myers aggregates the inserts and removes within a diff
            tokens_added = []
            tokens_deleted = []
            start, end = match.start(), match.end()
            for action, token in myers_diff[start:end]:
                if action == "i":
                    tokens_added.append(token)
                else:
                    tokens_deleted.append(token)
            location = block.a + first_file_indices[start]
            # Advance the location in the first file
            # Create a Diff object anchored at this location
            diff_map[location] = Diff(
                location=location,
                old=(tuple(tokens_deleted) if tokens_deleted else None),
                new=(tuple(tokens_added) if tokens_added else None),
            )

    if not check_reconstruction(first_tokens, last_tokens, diff_map):
        print("Diff error")
        return None

    return diff_map


def make_diffs(first_tokens_sentencized, last_tokens_sentencized):
    first_tokens = sum(first_tokens_sentencized, [])
    last_tokens = sum(last_tokens_sentencized, [])
    if first_tokens == last_tokens:
        diff_list = []
    else:

        diff_map = get_simple_diffs(first_tokens, last_tokens)
        if diff_map is None:
            diff_list = None
        diff_list = sorted(
            [d._asdict() for d in diff_map.values()], key=lambda x: x["location"]
        )

    return {
        "tokens": {FIRST: first_tokens_sentencized, LAST: last_tokens_sentencized},
        "diffs": diff_list,
    }
