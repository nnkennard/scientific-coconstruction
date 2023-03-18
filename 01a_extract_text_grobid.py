import argparse
import glob
import shutil
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
    "-d",
    "--data_dir",
    default="data/",
    type=str,
    help="output directory for metadata tsv, json, and pdf files",
)


def main():

    args = parser.parse_args()

    for filename in tqdm.tqdm(glob.glob(f"{args.data_dir}/{args.conference}/*/*.pdf")):
        new_filename = "pdfs/" + "___".join(filename.split("/")[-3:])
        shutil.copy(filename, new_filename)


if __name__ == "__main__":
    main()
