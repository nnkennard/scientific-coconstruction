import argparse
import glob
import json

parser = argparse.ArgumentParser(description="")
parser.add_argument("-d", "--data_dir", default="", type=str, help="")


def main():
    args = parser.parse_args()
    for filename in glob.glob(f'{args.data_dir}/*/diffs.json', 'r'):
        pass


if __name__ == "__main__":
    main()
