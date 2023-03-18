import argparse
import glob
import json
import stanza
import subprocess
import tqdm

import conference_lib as conflib


parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-c",
    "--conference",
    type=str,
    choices=conflib.CONFERENCE_TO_INVITATION.keys(),
    help="conference_year, e.g. iclr_2022",
)
parser.add_argument(
    "-f", "--offset", default=0, type=int, help="skip a number of submissions"
)
parser.add_argument(
    "-b",
    "--batch_size",
    default=None,
    type=int,
)
parser.add_argument(
    "-d",
    "--data_dir",
    default="data/",
    type=str,
    help="output directory for metadata tsv, json, and pdf files",
)
parser.add_argument("--debug", action="store_true", help="only process one batch")

STANZA_PIPELINE = stanza.Pipeline(
    "en",
    processors="tokenize",
)


def get_revision_map(raw_revision_map):
    revision_map = {}
    for a, b, c in raw_revision_map:
        if b is None or c is None:
            assert b is None and c is None
            revision_map[a] = None
        else:
            revision_map[a] = (b, c)
    return revision_map


PLACEHOLDER = "$$$$$$$$$$$$$"


def extract_text(pdf_path):
    output = subprocess.run(
        ["python", "pdfdiff.py", pdf_path], capture_output=True
    ).stdout
    return (
        output.decode()
        .replace("-\n", "")
        .replace("\n\n", PLACEHOLDER)
        .replace("\n", " ")
        .replace(PLACEHOLDER, "\n\n")
    )


def tokenize(text):
    doc = STANZA_PIPELINE(text)
    tokens = []
    for sentence in doc.sentences:
        tokens.append([token.to_dict()[0]["text"] for token in sentence.tokens])
    return tokens


def get_version_tokens(details):
    if details is None:
        return None
    else:
        path, date = details
        return tokenize(extract_text(path))


def get_text(obj):
    revision_map = get_revision_map(obj["versions"])
    for version, details in revision_map.items():
        tokens = get_version_tokens(details)
        if tokens is None:
            continue
        with open(details[0].replace(".pdf", ".txt"), "w") as f:
            for sent in tokens:
                f.write(" ".join(sent) + "\n")


def main():
    args = parser.parse_args()

    for forum_dir in tqdm.tqdm(list(glob.glob(f"{args.data_dir}/{args.conference}/*"))):
        with open(f"{forum_dir}/discussion2.json", "r") as f:
            obj = json.load(f)
            diffs = get_text(obj)


if __name__ == "__main__":
    main()
