import csv
import glob
import json
import sys


FIELDS = "forum index old_text new_text".split()

def convert_text(maybe_text):
    if maybe_text is None:
        return "NULL"
    else:
        return " ".join(maybe_text)


def main():
    with open('diffs_all.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for filename in glob.glob(f'{sys.argv[1]}/*/diffs.json'):
            with open(filename, 'r') as g:
                forum = filename.split("/")[-2]
                obj = json.load(g)
                if obj['diffs'] is not None:
                    for i, diff in enumerate(obj['diffs']):
                        writer.writerow(
                            {
                                "forum": forum,
                                "index": i,
                                "old_text": convert_text(diff['old']),
                                "new_text": convert_text(diff['new']),

                            }
                        )


if __name__ == "__main__":
    main()
    