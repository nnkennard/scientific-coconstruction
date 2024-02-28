import argparse
import glob
import os
import tqdm
import subprocess

import scc_lib

parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-d",
    "--data_dir",
    default="forums/",
    type=str,
    help="Data dir",
)

PLACEHOLDER = "$$$$$$$$$$$$$"


def extract_text(pdf_path):
    output = subprocess.run(["python", "pdfdiff.py", pdf_path],
                            capture_output=True).stdout
    return (output.decode().replace("-\n", "").replace(
        "\n\n", PLACEHOLDER).replace("\n", " ").replace(PLACEHOLDER, "\n\n"))


def main():
    args = parser.parse_args()
    for pdf_path in tqdm.tqdm(list(glob.glob(f"{args.data_dir}/*/*.pdf"))):
        if not os.path.isfile(f'{pdf_path[:-4]}_raw.txt'):
            text = extract_text(pdf_path)
            output_path = f'{pdf_path[:-4]}_raw.txt'
            with open(output_path, 'w') as f:
                f.write(text)


if __name__ == "__main__":
    main()
