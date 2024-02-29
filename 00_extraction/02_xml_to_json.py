import argparse
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

parser = argparse.ArgumentParser(description='')
parser.add_argument('-p', '--pdf_dir', default='', type=str, help='')

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

    return [section for section in sections]


def main():

    args = parser.parse_args()

    for initial_filename in tqdm.tqdm(
            list(glob.glob(f'{args.pdf_dir}/*/initial.xml'))):

        section_map = {}

        for version in ['initial', 'final']:
            xml_filename = initial_filename.replace('initial', version)
            output_filename = xml_filename.replace('.xml', '.json')
            try:
                sections = parse_xml(xml_filename)
                section_map[version] = sections
            except Exception as e:
                print(e)

        if len(section_map) == 2:

            a = list(x.title for x in section_map['initial'])
            b = list(x.title for x in section_map['final'])

            print(a == b)
            if not a == b:
                print(a)
                print(b)
                pass


if __name__ == "__main__":
    main()
