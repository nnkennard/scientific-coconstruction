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
                    default="v3/bundles/",
                    type=str,
                    help="")

CONTEXT_SIZE = 20

OLD_START, OLD_END, NEW_START, NEW_END = [f"<{label}>"
    #for label in "old /old new /new".split()]
    for label in "diffdel /diffdel diffadd /diffadd".split()]

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


def get_diff_text(diff, flat_initial_tokens):
    old_tokens, new_tokens = get_all_tokens(diff)
    diff_start = diff["location"]
    diff_end = diff_start + len(old_tokens)
    start_window_size = max(0, diff_start - CONTEXT_SIZE)
    before_context = " ".join(
        flat_initial_tokens[start_window_size:diff_start])
    old = " ".join(old_tokens)
    new = " ".join(new_tokens)
    after_context = " ".join(flat_initial_tokens[diff_end:diff_end +
                                                 CONTEXT_SIZE])

    return " ".join([
        before_context, "<diffdel>", old, "</diffdel> <diffadd>", new,
        "</diffadd>", after_context
    ])


def save_raw_samples(output_dir, data_dir, forum):
    raw_dir = f'{output_dir}/raw_{forum}'
    shutil.copytree(f'{data_dir}/{forum}/', raw_dir)
    with tarfile.open(
          os.path.normpath(f'{output_dir}/raw_{forum}.tgz'),
          "w:gz") as tar:
        tar.add(raw_dir, arcname=f'raw_{forum}/')
    shutil.rmtree(raw_dir)

def highlight_diffs(diffs_obj):

    flat_initial_tokens = sum(diffs_obj['tokens']['initial'], [])
    first_diff_start = diff_objs['diffs'][0]['location']
    highlighted_tokens = flat_initial_tokens[:first_diff_start]

    diff_anchors = []
    new_i = len(highlighted_tokens)
    for diff in diffs_obj['diffs']:
        start = len(highlighted_tokens)
        old, new = get_all_tokens(diff)
        if old:
            highlighted_tokens += [OLD_START] + old + [OLD_END]
        if new:
            highlighted_tokens += [NEW_START] + new + [NEW_END]
        end = len(highlighted_tokens)
        diff_anchors.append((star, end, diff))

    final_diff =  diff_objs['diffs'][-1]
    final_diff_old, _ = get_all_tokens(final_diff)
    final_diff_end = final_diff['location'] + len(final_diff_old)
    highlighted_tokens += flat_initial_tokens[final_diff_end:]

    return highlighted_tokens, diff_anchors

def complete_bundle(forum, diff_index):
    for aux_file in ["style.css", "0.html", "last.html"]:
        shutil.copyfile(
                f"templates/{aux_file}",
                f'{args.output_dir}/bundle_{forum}/{aux_file}')
        shutil.move(f'{args.output_dir}/bundle_{forum}/last.html',
                    f'{args.output_dir}/bundle_{forum}/{diff_index}.html')

    source_dir = f'{args.output_dir}/bundle_{forum}/'
    with tarfile.open(os.path.normpath(
        f'{args.output_dir}/bundle_{forum}.tgz'), "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    shutil.rmtree(source_dir)

def build_core_bundle(diff_dir):
    forum = diff_dir.split("/")[-2]

    #save_raw_samples(args.output_dir, args.data_dir, forum)
    #continue

    with open(f'{args.data_dir}/{forum}/diffs.json', 'r') as f:
        obj = json.load(f)
    highlighted_tokens, diff_map = highlight_diffs(obj)

    os.makedirs(f'{args.output_dir}/bundle_{forum}', exist_ok=True)
    initial_tokens = obj['tokens']['initial']
    flat_initial_tokens = sum(initial_tokens, [])
    diff_index = 1
    for diff in tqdm.tqdm(obj['diffs']):
        diff_identifier = f'{forum}|||{diff_index}'
        diff_text = get_diff_text(diff, flat_initial_tokens)
        html_text = str(TEMPLATE_TEXT).replace(
            "DIFF_IDENTIFIER",
            diff_identifier).replace("DIFF_TEXT", diff_text).replace(
                "PREV_INDEX", str(diff_index - 1)).replace(
                    "NEXT_INDEX", str(diff_index + 1)).replace(
                        "ICLR_LINK",
                        f"https://openreview.net/forum?id={forum}")
        with open(
                f'{args.output_dir}/bundle_{forum}/{diff_index}.html',
                'w') as f:
            f.write(html_text)
        diff_index += 1
    return forum, diff_index



def main():

    args = parser.parse_args()
    for diff_dir in sorted(glob.glob(f"{args.data_dir}/*/"))[:10]:
        forum, diff_index = build_core_bundle(diff_dir)
        complete_bundle(forum, diff_index)

if __name__ == "__main__":
    main()
