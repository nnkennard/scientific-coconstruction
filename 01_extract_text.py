import argparse
import glob
from tqdm import tqdm
import subprocess

import scc_lib

from google.cloud import bigquery
from google.cloud import storage
import os
import pandas as pd

parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-d",
    "--data_dir",
    default="forums/",
    type=str,
    help="Data dir",
)

PLACEHOLDER = "$$$$$$$$$$$$$"


# ------------------------------------------------------------------------
# eLife via GoogleStorage
# ------------------------------------------------------------------------

# Instantiates client
GOOGLE_STORAGE = storage.Client()

# The name for the new bucket
BUCKET_NAME = "mimir-elife-pdfs"

# Link to the bucket
bucket = GOOGLE_STORAGE.bucket(BUCKET_NAME)


def return_paths(blob_list):
    """
    Takes a list of Storage blobs;
    Returns list of Storage file paths
    """
    return [blob.name for blob in blob_list]


def get_ms_id(pdf_path: str) -> int:
    """
    Takes list of Storage file paths of regular structure;
    Returns MS id
    """
    try:
        path_parts = pdf_path.split("/")
        # file names are uninformative
        # ms info lives in dir name of file
        ms_info = path_parts[-2]
        # usually, MS id is in final position of dir
        ms_id = ms_info.split("-")[-1]
        return int(ms_id)
    
    except:
        # about 3 (of 10s thousands) that don't conform
        print(f"dropping {pdf_path}")


def make_df(paths_list, stage):
    """
    Takes a list of paths of MSes at a given stage ("initial" or "accepted"),
    Returns a pandas df with ms_id and the stage-specific path
    """
    dct_lst = list()
    for i, pdf_path in enumerate(tqdm(paths_list)):
        dct = dict()
        dct[f"{stage}_path"] = pdf_path
        dct["ms"] = get_ms_id(pdf_path)
        dct_lst.append(dct)
    return pd.DataFrame(dct_lst)


def get_storage_paths():
    """
    Returns a dct of the following form:
    {ms_id_int: {"initial_path": "PATH",
                 "accepted_path": "PATH"}}
    """

    dfs_dct = {}
    for prefix in "initial_submissions/ accepted_submissions/".split():
        stage = prefix.split("_")[0]

        # get blob objects corresponding to MSes at each stage
        blob_list = GOOGLE_STORAGE.list_blobs(BUCKET_NAME, prefix=prefix)

        # get their relative Storage paths
        paths = return_paths(blob_list)

        # make df for fast manipulation of ms paths
        df = make_df(paths[:10], stage)

        # There are ~1000 duplicated ms_ids across stages
        # We'll keep first one
        # TODO: Explore these!
        df = df.drop_duplicates(subset="ms")
        dfs_dct[stage] = df

    # Merge
    path_df = dfs_dct["accepted"].merge(
        dfs_dct["initial"], how="left", on="ms", validate="one_to_one"
    )

    # Drop if missing path; few (~3)
    path_df.dropna(inplace=True)

    # Convert to dct:
    return path_df.set_index("ms").to_dict(orient="index")


def make_local_dir(data_dir, ms_id):
    """
    Creates subdir for ms_id
    """
    try:
        os.makedirs(data_dir + f"ms_{ms_id}/")
        return data_dir + f"ms_{ms_id}/"
    except FileExistsError:
        # directory already exists
        print("directory already exists; contents will be overwritten")
        return data_dir + f"ms_{ms_id}/"


# ------------------------------------------------------------------------


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


def main():
    args = parser.parse_args()

    # get all dct of ms_id and its storage paths
    storage_paths_dct = get_storage_paths()

    for ms_id, paths_dct in tqdm(storage_paths_dct.items()):

        # make local dir and get local pdf_path
        local_dir = make_local_dir(args.data_dir, ms_id)

        for stage, storage_path in paths_dct.items():
            
            cleaned_stage = stage.split("_")[0]

            # summon blob object
            blob = bucket.blob(storage_path)

            # hack to move blob data to local dir
            pdf_path = local_dir + f"{ms_id}_{cleaned_stage}"
            
            with blob.open("rb") as raw_blob:
                with open(f"{pdf_path}.pdf", "wb") as temp:
                    temp.write(raw_blob.read())

            text = extract_text(pdf_path)
            # os.remove(f"{pdf_path}.pdf")
            output_path = f"{pdf_path}.txt"
            with open(output_path, "w") as f:
                f.write(text)


if __name__ == "__main__":
    main()
