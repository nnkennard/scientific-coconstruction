# scientific-coconstruction

## Setup

pip-install the requirements. This code has been tested with an environment using Python 3.8.

```
python -m pip install -r requirements.txt
python -c "import stanza; stanza.download('en')"
```

## Gathering raw data

First, gather raw PDFs, linking different revisions. PDFs should be saved in a directory with the following structure:

```
[data_directory]/
  └─── [ms_identifier_1]/
        │    pre-rebuttal_revision.pdf
        │    <rebuttal_revision.pdf> # optional
        │    final_revision.pdf
        └─── discussion.json
  └─── [ms_identifier_2]/
        │    pre-rebuttal_revision.pdf
        │    <rebuttal_revision.pdf> # optional
        │    final_revision.pdf
        └─── discussion.json
  └─── ...
```

`discussion.json` should be a json file in the following format:
```
{
  "forum_id": <forum_id>,
  "versions": [
                [
                  <version_name>,
                  <path_to_pdf>,
                  <timestamp>
                ],
                [
                  <version_name>,
                  <path_to_pdf>,
                  <timestamp>
                ],
                ...
              ]
}
```

To use pdfs from OpenReview, run:

```
python 00_get_openreview_data.py -c [conference_name] -d [data_directory]
```



## Extracting text

We extract text from pdfs using [pdfdiff](https://github.com/cascremers/pdfdiff/blob/master/pdfdiff.py), but ironically, we do not use it to extract the diffs. Pdfdiff does a pretty good job of [dehyphenation](https://www.semanticscholar.org/paper/Improved-Dehyphenation-of-Line-Breaks-for-PDF-Text-Korzen/754758fc0f8ff1f52a94288256ec947cabb50270), does not drop any text, and does not get confused by captions.

To extract text from all the pdfs, run 

```
python 01_extract_text.py -c [conference_name] -d [data_directory]
```

## Extracting diffs

```
python 02_extract_diffs.py -c [conference_name] -d [data_directory]
python 03_merge_diffs.py -c [conference_name] -d [data_directory]
```

