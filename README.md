# Scientific co-construction

The code in this directory is separated into three parts:

1) Extraction: includes downloading data from OpenReview, parsing manuscript versions, extracting the diffs from the parsed manuscripts. The first steps can be bypassed so that non-OpenReview (i.e. LSJ) manuscripts can be used.

2) Analysis: includes taxonomizing the diffs, analyzing the structure of manuscripts into sections and the relation between diffs and sections.

3) Linking: linking review comments to diffs using BM25.

The code in the extraction section also includes extraction of information about authors. This information will be used later.
