import argparse
import glob
import json
import sys
import re
import tqdm

parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-d",
    "--data_dir",
    default="forums/",
    type=str,
    help="Data dir",
)

UNDER_REVIEW_RE = re.compile(
    "Under review as a conference paper at ICLR 20[0-9]{2}")
PUBLISHED_RE = re.compile("Published as a conference paper at ICLR 20[0-9]{2}")
ABSTRACT_HEADER_RE = re.compile("^A\sBSTRACT")
SECTION_HEADER_RE = re.compile("^[A-Z]\s?[A-Z+]")


def mostly_caps(line):
    letters = "".join(line.split())
    return len([x for x in letters if x.isupper()]) / len(letters) > 0.8


def clean_file(filename):

    with open(filename, 'r') as f:
        lines = [line.strip() for line in f.readlines()]

    curr_page_num = 0
    final_lines = []

    abstract_seen = False
    for i in range(len(lines)):
        line = lines[i]
        if not line:
            continue
        if line.startswith("R EFERENCES"):
            # References starting. We are done.
            break
        if UNDER_REVIEW_RE.match(line) or PUBLISHED_RE.match(line):
            if i > 2:
                #assert not lines[i-1]
                next_page_num = str(curr_page_num + 1)
                curr_page_num += 1
                temp = final_lines.pop(-1)
                if temp.endswith(next_page_num):
                    final_lines.append(temp[:-len(next_page_num)])
                else:
                    final_lines.append(temp)
                continue
        #elif ABSTRACT_HEADER_RE.match(line):
        #    abstract_seen = True
        #    final_lines.append(line)
        #elif abstract_seen and SECTION_HEADER_RE.match(line):
        #    print("*", final_lines[-1])
        #    if mostly_caps(line) and final_lines[-1][-1].isnumeric():
        #        prev_line = final_lines.pop(-1)
        #        rev_sec_num = re.search("^([0-9](\s\.[0-9]+)*)",
        #        prev_line[::-1]).group(1)
        #        final_lines.append(
        #            prev_line[:-len(rev_sec_num)])
        #    final_lines.append(line)
        else:
            final_lines.append(line)

    return "\n".join(final_lines)


def main():
    args = parser.parse_args()
    for filename in tqdm.tqdm(list(glob.glob(f'{args.data_dir}/*/*_raw.txt'))):
        with open(filename.replace("_raw", ""), 'w') as f:
            f.write(clean_file(filename))


if __name__ == "__main__":
    main()
