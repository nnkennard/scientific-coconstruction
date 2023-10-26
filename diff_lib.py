import collections
import difflib
import myers
import re

import scc_lib

Diff = collections.namedtuple("Diff",
                              "location old new",
                              defaults=(None, None, None))
NonMatchingBlock = collections.namedtuple("NonMatchingBlock",
                                          "a, b, a_len, b_len")


def check_reconstruction(initial_tokens, final_tokens, diff_map):
    """Helper to apply diffs to original tokens and check against final tokens.
    Args:
        initial_tokens: list of strings representing original tokens
        final_tokens: list of strings representing modified tokens
        diff_map: map from initial_tokens index to Diff object.

    Returns:
        True if the diffs correctly map the changes, otherwise False.
    """
    constructed_final_tokens = []

    i = 0
    while i < len(initial_tokens):
        if i not in diff_map:
            # No diff at this location
            constructed_final_tokens.append(initial_tokens[i])
            i += 1
        else:
            diff = diff_map[i]
            if diff.old is None:
                # This is an insertion diff, insert after the token at this location
                constructed_final_tokens.append(initial_tokens[i])
                i += 1
            else:
                # This is a deletion or modification diff. Skip some of initial tokens
                i += len(diff.old)
            if diff.new is not None:
                # Insertion or modification diff. Add inserted tokens
                constructed_final_tokens += list(diff.new)

    return constructed_final_tokens == final_tokens


def get_matching_blocks(initial_tokens, final_tokens):
    matching_blocks = difflib.SequenceMatcher(
        None, initial_tokens, final_tokens).get_matching_blocks()

    if matching_blocks[0][:2] != (0, 0):
        # The pair does not start with a matching block, add a placeholder
        matching_blocks = [(0, 0, 0)] + matching_blocks

    return [tuple(b) for b in matching_blocks]


def get_non_matching_blocks(matching_blocks, min_len, initial_len, final_len):
    non_matching_blocks = []
    last_index_initial = 0
    last_index_final = 0
    for initial_i, final_i, matching_size in matching_blocks:
        if matching_size >= min_len:
            # The matching block is not just a blip amidst a diff. It is large
            # enough to delimit two separate nonmatching blocks. We add the
            # preceding nonmatching block.
            non_matching_blocks.append(
                NonMatchingBlock(
                    last_index_initial,
                    last_index_final,
                    initial_i - last_index_initial,
                    # The length of the nonmatching block in the
                    # initial text
                    final_i - last_index_final,
                    # The length of the nonmatching block in the
                    # final text
                ))
            # Advance the cursors by the length of the matching block
            last_index_initial = initial_i + matching_size
            last_index_final = final_i + matching_size

    # In case the lists end in a nonmatching block
    if initial_len > last_index_initial or final_len > last_index_final:
        non_matching_blocks.append(
            NonMatchingBlock(
                last_index_initial,
                last_index_final,
                initial_len - last_index_initial,
                final_len - last_index_final,
            ))

    # There was some code here that should actually never be triggered because
    # of the way get_matching_blocks adds a final empty matching block if
    # necessary. Replaced with an assert (should work)
    assert last_index_initial + 1 == initial_len and last_index_final + 1 == final_len

    return non_matching_blocks


def parse_myers_diff(myers_diff, block_start):

    # The result is a list of (action, line) pairs,
    # where action is one of KEEP, INSERT, REMOVE, or OMIT
    # (which happen to be the characters k, i, r, and o).
    # There is a line for each token in the initial and final tokens lists
    # (same line, with a k, if the line is unchanged)

    initial_file_indices = []
    # Which index in the initial token list each Myers diff line is anchored to
    current_initial_file_index = -1

    # For each token in the diff, find the token index it should be anchored to
    # in the initial file.
    for action, token in myers_diff:
        if action in "kr":
            current_initial_file_index += 1  # keep and remove advance by one index
        initial_file_indices.append(current_initial_file_index)

    action_string = "".join(x[0] for x in myers_diff)
    assert len(action_string) == len(initial_file_indices)

    diff_map = {}
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
        location = block_start + initial_file_indices[start]
        # Advance the location in the initial file
        # Create a Diff object anchored at this location
        diff_map[location] = Diff(
            location=location,
            old=(tuple(tokens_deleted) if tokens_deleted else None),
            new=(tuple(tokens_added) if tokens_added else None),
        )
    return diff_map


def get_myers_diffs(non_matching_blocks, initial_tokens, final_tokens,
                    max_len):
    # Map from indices in initial_tokens to diffs at that index
    diff_map = {}
    for block in sorted(non_matching_blocks):
        # Get non matching tokens from initial and final text
        mini_initial = initial_tokens[block.a:block.a + block.a_len]
        mini_final = final_tokens[block.b:block.b + block.b_len]
        if abs(block.b_len - block.a_len) < max_len:
            # Find maximal diffs in the nonmatching block
            myers_diff = myers.diff(mini_initial, mini_final)
            block_diff_map = parse_myers_diff(myers_diff, block.a)
            diff_map.update(block_diff_map)
        else:
            # This is a very large diff, it's not worth it to get the Myers
            # diff. Just replace the whole original sequence with the whole
            # final sequence
            deleted_tokens = mini_initial
            added_tokens = mini_final
            diff_map[block.a] = Diff(
                location=block.a,
                old=(tuple(deleted_tokens) if deleted_tokens else None),
                new=(tuple(added_tokens) if added_tokens else None),
            )
    return diff_map


def factored_simple_diffs(initial_tokens,
                          final_tokens,
                          min_len=5,
                          max_len=2000):
    matching_blocks = get_matching_blocks(initial_tokens, final_tokens)
    non_matching_blocks = get_non_matching_blocks(matching_blocks, min_len,
                                                  len(initial_tokens),
                                                  len(final_tokens))
    diff_map = get_myers_diffs(non_matching_blocks, initial_tokens,
                               final_tokens, max_len)
    check_reconstruction(initial_tokens, final_tokens, diff_map)
    return diff_map


def make_diffs(initial_tokens, final_tokens):
    if initial_tokens == final_tokens:
        diff_list = []
    else:
        diff_map = factored_simple_diffs(initial_tokens, final_tokens)
        if diff_map is None:  # An error has occurred?
            diff_list = None
        else:
            diff_list = sorted([d._asdict() for d in diff_map.values()],
                               key=lambda x: x["location"])

    return {
        "tokens": {
            scc_lib.INITIAL: initial_tokens,
            scc_lib.FINAL: final_tokens
        },
        "diffs": diff_list,
    }
