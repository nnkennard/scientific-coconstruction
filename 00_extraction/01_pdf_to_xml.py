import argparse
import glob
import os
import shutil
import tqdm

from sciencebeam_parser.resources.default_config import DEFAULT_CONFIG_FILE
from sciencebeam_parser.config.config import AppConfig
from sciencebeam_parser.utils.media_types import MediaTypes
from sciencebeam_parser.app.parser import ScienceBeamParser

parser = argparse.ArgumentParser(description='')
parser.add_argument('-p', '--pdf_dir', default='', type=str, help='')


def main():

    args = parser.parse_args()

    config = AppConfig.load_yaml(DEFAULT_CONFIG_FILE)
    sciencebeam_parser = ScienceBeamParser.from_config(config)

    for initial_filename in tqdm.tqdm(
            list(glob.glob(f'{args.pdf_dir}/*/initial.pdf'))):

        for filename in [
                initial_filename,
                initial_filename.replace('initial.pdf', 'final.pdf')
        ]:
            output_filename = filename.replace('.pdf', '.xml')
            if os.path.exists(output_filename):
                continue

            try:
                with sciencebeam_parser.get_new_session() as session:
                    session_source = session.get_source(
                        filename, MediaTypes.PDF)
                    converted_file = session_source.get_local_file_for_response_media_type(
                        MediaTypes.TEI_XML)
                    shutil.copyfile(converted_file, output_filename)
            except Exception as e:
                print("Error", filename)
                dsds


if __name__ == "__main__":
    main()
