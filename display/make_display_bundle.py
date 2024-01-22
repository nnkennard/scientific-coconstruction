import argparse
import glob
import json
import os
import shutil
import tarfile

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")
parser.add_argument("-o",
                    "--output_dir",
                    default="bundles/",
                    type=str,
                    help="")

CONTEXT_SIZE = 20


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


def main():

    args = parser.parse_args()

    with open('templates/template.html', 'r') as f:
        template_text = f.read()

    for diff_dir in sorted(glob.glob(f"{args.data_dir}/*/"))[:10]:
        forum = diff_dir.split("/")[-2]
        print(forum)
        os.makedirs(f'{args.output_dir}/bundle_{forum}', exist_ok=True)
        with open(f'{args.data_dir}/{forum}/diffs.json', 'r') as f:
            obj = json.load(f)
            initial_tokens = obj['tokens']['initial']
            flat_initial_tokens = sum(initial_tokens, [])
            diff_index = 1
            for diff in obj['diffs'][:10]:
                print(diff_index)
                diff_identifier = f'{forum}|||{diff_index}'
                diff_text = get_diff_text(diff, flat_initial_tokens)
                html_text = str(template_text).replace(
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
            for aux_file in ["style.css", "0.html", "last.html"]:
                shutil.copyfile(
                    f"templates/{aux_file}",
                    f'{args.output_dir}/bundle_{forum}/{aux_file}')
            shutil.move(f'{args.output_dir}/bundle_{forum}/last.html',
                        f'{args.output_dir}/bundle_{forum}/{diff_index}.html')
            source_dir = f'{args.output_dir}/bundle_{forum}/'
            with tarfile.open(
                    os.path.normpath(f'{args.output_dir}/bundle_{forum}.tgz'),
                    "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))


if __name__ == "__main__":
    main()
