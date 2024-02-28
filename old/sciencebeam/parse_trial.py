import collections
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
    print(parse_xml('xml_demo.xml'))


if __name__ == "__main__":

    main()
