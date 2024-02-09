import argparse
import glob
import json
import os
import shutil
import tarfile
import tqdm

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")
parser.add_argument("-o",
                    "--output_dir",
                    default="v5/bundles/",
                    type=str,
                    help="")

CONTEXT_SIZE = 20

MAIN_TAGS = {
    "open": {
        "old": "<diffdel>",
        "new": "<diffadd>",
    },
    "close": {
        "old": "</diffdel>",
        "new": "</diffadd>",
    },
}

MAIN_TAG_SET = list(MAIN_TAGS['open'].values()) + list(
    MAIN_TAGS['close'].values())

BG_TAGS = {
    "open": {
        "old": "<bgdel>",
        "new": "<bgadd>",
    },
    "close": {
        "old": "</bgdel>",
        "new": "</bgadd>",
    },
}


def main_to_background(tag):
    return tag.replace('diff', 'bg')


with open('templates/template.html', 'r') as f:
    TEMPLATE_TEXT = f.read()


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


def save_raw_samples(output_dir, data_dir, forum):
    raw_dir = f'{output_dir}/raw_{forum}'
    shutil.copytree(f'{data_dir}/{forum}/', raw_dir)
    with tarfile.open(os.path.normpath(f'{output_dir}/raw_{forum}.tgz'),
                      "w:gz") as tar:
        tar.add(raw_dir, arcname=f'raw_{forum}/')
    shutil.rmtree(raw_dir)


def highlight_diffs(diffs_obj):

    if not diffs_obj['diffs']:
        return [], []

    flat_initial_tokens = sum(diffs_obj['tokens']['initial'], [])
    first_diff_start = diffs_obj['diffs'][0]['location']
    highlighted_tokens = flat_initial_tokens[:first_diff_start]

    for i, t in enumerate(flat_initial_tokens):
        print("((", i, t)

    diff_anchors = []
    for i, diff in enumerate(diffs_obj['diffs']):
        #print("=" * 80)`
        print(diff)
        start = len(highlighted_tokens)
        #print(highlighted_tokens[-1])
        #print("Start in new token list:" , start)
        for old_new in ['old', 'new']:
            if diff[old_new] is None or not diff[old_new]:
                #print("Nothing in ", old_new)
                continue
            #print("*", [
            #    MAIN_TAGS['open'][old_new]
            #] + diff[old_new] + [MAIN_TAGS['close'][old_new]])

            highlighted_tokens += [
                MAIN_TAGS['open'][old_new]
            ] + diff[old_new] + [MAIN_TAGS['close'][old_new]]
        end = len(highlighted_tokens)
        diff_anchors.append((start, end, diff))
        if i == len(diffs_obj['diffs']) - 1:
            continue
        old, new = get_all_tokens(diff)
        print(old, new)

        # in between start
        if old:
            in_between_start = diff['location'] + len(old)
        else:
            in_between_start = diff['location'] + 1

        # in between end
        next_diff = diffs_obj['diffs'][i + 1]
        old, new = get_all_tokens(next_diff)
        if old:  # something is deleted
            in_between_end = next_diff["location"]
        else:
            in_between_end = next_diff["location"] + 1

        # first token from old tokens (after diff)

        in_between_part = flat_initial_tokens[in_between_start:in_between_end]
        print("in between part")
        print(" ".join(in_between_part))
        highlighted_tokens += in_between_part

    final_diff = diffs_obj['diffs'][-1]
    final_diff_old, _ = get_all_tokens(final_diff)
    final_diff_end = final_diff['location'] + len(final_diff_old)
    highlighted_tokens += flat_initial_tokens[final_diff_end:]

    for t in highlighted_tokens:
        print("##", t)

    return highlighted_tokens, diff_anchors


def complete_bundle(forum, diff_index, output_dir):
    for aux_file in ["style.css", "0.html", "last.html"]:
        shutil.copyfile(f"templates/{aux_file}",
                        f'{output_dir}/bundle_{forum}/{aux_file}')
    shutil.move(f'{output_dir}/bundle_{forum}/last.html',
                f'{output_dir}/bundle_{forum}/{diff_index}.html')

    source_dir = f'{output_dir}/bundle_{forum}/'
    with tarfile.open(os.path.normpath(f'{output_dir}/bundle_{forum}.tgz'),
                      "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    shutil.rmtree(source_dir)


def backgroundize_highlights(tokens):
    backgroundized_tokens = []
    for token in tokens:
        if token in MAIN_TAG_SET:
            backgroundized_tokens.append(main_to_background(token))
        else:
            backgroundized_tokens.append(token)

    add_start = None
    for token in backgroundized_tokens:
        if token in BG_TAGS['open'].keys():  # encountering open tag first
            break
        if token in BG_TAGS['close'].keys():  # encountering close tag first
            add_start = token.replace("/", "")
            break

    if add_start is not None:
        backgroundized_tokens = [add_start] + backgroundized_tokens

    add_end = None
    for token in backgroundized_tokens[::-1]:
        if token in BG_TAGS['close'].keys():  # encountering close tag first
            break
        if token in BG_TAGS['open'].keys():  # encountering close tag first
            add_end = token.replace("<b", "</b")

    if add_end is not None:
        backgroundized_tokens.append(add_end)

    return " ".join(backgroundized_tokens)


def build_core_bundle(diff_dir, data_dir, output_dir):
    forum = diff_dir.split("/")[-2]

    #save_raw_samples(args.output_dir, args.data_dir, forum)
    #continue

    with open(f'{data_dir}/{forum}/diffs.json', 'r') as f:
        obj = json.load(f)
    highlighted_tokens, diff_map = highlight_diffs(obj)

    os.makedirs(f'{output_dir}/bundle_{forum}', exist_ok=True)

    diff_index = 1
    for start, end, diff in diff_map:
        diff_tokens = " ".join(highlighted_tokens[start:end])
        before = backgroundize_highlights(
            highlighted_tokens[start - CONTEXT_SIZE:start])
        after = backgroundize_highlights(highlighted_tokens[end:end +
                                                            CONTEXT_SIZE])

        diff_text = " ".join([before, diff_tokens, after])
        diff_identifier = f'{forum}|||{diff_index}'
        html_text = str(TEMPLATE_TEXT).replace(
            "DIFF_IDENTIFIER", diff_identifier).replace(
                "DIFF_TEXT",
                diff_text).replace("PREV_INDEX", str(diff_index - 1)).replace(
                    "NEXT_INDEX", str(diff_index + 1)).replace(
                        "ICLR_LINK",
                        f"https://openreview.net/forum?id={forum}")
        with open(f'{output_dir}/bundle_{forum}/{diff_index}.html', 'w') as f:
            f.write(html_text)
        diff_index += 1
    return forum, diff_index


def main():

    args = parser.parse_args()
    for diff_dir in sorted(glob.glob(f"{args.data_dir}/*/"))[:10]:
        if 'rcO' in diff_dir:
            #if True:
            print(diff_dir)
            forum, diff_index = build_core_bundle(diff_dir, args.data_dir,
                                                  args.output_dir)
            complete_bundle(forum, diff_index, args.output_dir)


if __name__ == "__main__":
    main()
