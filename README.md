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
[output_directory]/
  └─── [ms_identifier_1]/
        │    pre-rebuttal_revision.pdf
        │    rebuttal_revision.pdf
        │    final_revision.pdf
        └─── discussion.json
  └─── [ms_identifier_2]/
        │    pre-rebuttal_revision.pdf
        │    rebuttal_revision.pdf
        │    final_revision.pdf
        └─── discussion.json
  └─── ...
```

To use pdfs from OpenReview, run:

```
python 00_get_openreview_data.py -c [conference_name] -d [output_directory]
```

## Extracting 
