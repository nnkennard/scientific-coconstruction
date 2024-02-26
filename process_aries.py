import argparse
import json
import os
import requests
import tqdm

import scc_lib

parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-o",
    "--output_dir",
    default="aries_forums/",
    type=str,
    help="Data dir",
)
parser.add_argument(
    "-i",
    "--input_file",
    default=
    "/work/pi_mccallum_umass_edu/nnayak_umass_edu/aries/data/aries/paper_edits.jsonl",
    type=str,
    help="path to ARIES paper_edits.jsonl",
)


def write_pdf_to_dir(forum_path, pdf_id, initial_final):
    url = f'https://openreview.net/references/pdf?id={pdf_id}'
    filename = f'{forum_path}/{initial_final}.pdf'
    r = requests.get(url)
    open(filename, 'wb').write(r.content)


def main():

    args = parser.parse_args()

    with open(args.input_file, 'r') as f:
        lines = f.readlines()
        for line in tqdm.tqdm(lines):
            obj = json.loads(line)
            forum_path = f'{args.output_dir}/{obj["doc_id"]}/'
            os.makedirs(forum_path, exist_ok=True)
            write_pdf_to_dir(forum_path, obj['source_pdf_id'], scc_lib.INITIAL)
            write_pdf_to_dir(forum_path, obj['target_pdf_id'], scc_lib.FINAL)


if __name__ == "__main__":
    main()
