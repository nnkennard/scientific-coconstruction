from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull

from sciencebeam_parser.resources.default_config import DEFAULT_CONFIG_FILE
from sciencebeam_parser.config.config import AppConfig
from sciencebeam_parser.utils.media_types import MediaTypes
from sciencebeam_parser.app.parser import ScienceBeamParser

import collections
import glob
import json
import os
import tqdm
import xml.etree.ElementTree as ET

PREFIX = "{http://www.tei-c.org/ns/1.0}"
TEXT_ID = f"{PREFIX}text"
BODY_ID = f"{PREFIX}body"
DIV_ID = f"{PREFIX}div"
HEAD_ID = f"{PREFIX}head"
P_ID = f"{PREFIX}p"
NOTE_ID = f"{PREFIX}note"
FORMULA_ID = f'{PREFIX}formula'

Section = collections.namedtuple("Section", "title number text".split())


class Section(object):
    def __init__(self, title, number, text):
        self.title = title
        self.number = number
        self.text = text

    def as_json(self):
        return {'title': self.title, 'number': self.number, 'text': self.text}


def parse_xml(filename):
    sections = []

    divs = (ET.parse(filename).getroot().findall(TEXT_ID)[0].findall(BODY_ID)
            [0].findall(DIV_ID))
    for div in divs:
        (header_node, ) = div.findall(HEAD_ID)
        maybe_section_number = header_node.attrib.get('n', None)
        maybe_section_title = header_node.text

        text = []
        for p in div.findall("*"):
            if p.tag in [P_ID, NOTE_ID]:
                text.append(" ".join(p.itertext()))
            if p.tag == FORMULA_ID:
                text.append("$$FORMULA$$")

        if maybe_section_number is None:
            sections[-1].text += [maybe_section_title]
            sections[-1].text += text
            pass
        else:
            sections.append(
                Section(maybe_section_title, maybe_section_number, text))

    return [section.as_json() for section in sections]


def main():
    config = AppConfig.load_yaml(DEFAULT_CONFIG_FILE)
    sciencebeam_parser = ScienceBeamParser.from_config(config)

    for initial_filename in tqdm.tqdm(
        list(
        glob.glob('/gypsum/work1/mccallum/nnayak/forums/*/initial.pdf'))):

        for filename in [initial_filename,
            initial_filename.replace('initial.pdf', 'final.pdf')]:
            output_filename = filename.replace('.pdf', '_sbraw.json')
            if os.path.exists(output_filename):
                continue

            try:
                with sciencebeam_parser.get_new_session() as session:
                    session_source = session.get_source(
                        filename, MediaTypes.PDF)
                    converted_file = session_source.get_local_file_for_response_media_type(
                        MediaTypes.TEI_XML)
                    with open(output_filename, 'w') as f:
                        json.dump(parse_xml(converted_file), f)
            except Exception as e:
                print("Error", filename)
if __name__ == "__main__":
    main()
