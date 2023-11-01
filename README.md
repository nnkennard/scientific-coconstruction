# Scientific Co-construction

Sadly this entire repository is still itself under construction, BUT the code to extract fine-grained diffs from PDF pairs is done.

## Fine-grained diff extraction

1. Setup:
```
conda create
conda activate
python -m pip install -r requirements.txt
```

2. Prepare your data:
Create a directory containing the PDF pairs, each under a subdirectory bearing an identifier:
```
scientific-coconstruction/
└─── my_pdf_pairs/
     └─── pdf_identifier_1/
          | initial.pdf  
          | final.pdf
     └─── pdf_identifier_2/
          | initial.pdf  
          | final.pdf
     └─── ...
```

3. Extract text:
```
python 01_extract_text.py -d my_pdf_pairs/
```
This script creates `initial.txt` and `final.txt` in each subdirectory of `my_pdf_pairs`.

4. Extract diffs:
```
python 02_extract_diffs.py -d my_pdf_pairs/
```
This script creates `diffs.json` in each subdirectory of `my_pdf_pairs`.
