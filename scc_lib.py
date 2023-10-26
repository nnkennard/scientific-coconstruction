import stanza

SENTENCIZE_PIPELINE = stanza.Pipeline("en", processors="tokenize")


class Conference(object):
    iclr_2018 = "iclr_2018"
    iclr_2019 = "iclr_2019"
    iclr_2020 = "iclr_2020"
    iclr_2021 = "iclr_2021"
    iclr_2022 = "iclr_2022"
    ALL = [iclr_2018, iclr_2019, iclr_2020, iclr_2021, iclr_2022]


INITIAL, FINAL = "initial final".split()
