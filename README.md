# PDF extractor based on pyMuPdf
TyrannoText is a simple pdf extractor based on pyMuPDF. The main feature is to automatically merge text nodes in 
order to recover the page layout. The merge is bases on simple rules based on the type of text nodes.

There 4 four type of text nodes:
- `TyrannoSpan` represent the smallest sequence of character detected by pyMuPDF; usually, it corresponds to a word.
- `TyrannoLine` represents a line of text; it is obtained by merging spans with the same font that are on the same line;
- `TyrannoParagraph` represents a paragraph; it is obtained by merging lines with the same font that are close 
  vertically and aligned horizontally (left, center or right);
- `TyrannoColumn` represents a column: it is obtained by merging paragraph that are aligned horizontally;
- `TyrannoPage` represents a page of text; it is made up of columns.

The extraction is carried out by `TyrannoExtractor`; during its initialisation, you can specify some 
hyperparameters which affect the result (e.g. the maximum distance to merge two spans, etc...).
Check [this notebook](examples/first_example.ipynb) to see some examples of usages!

**It is a very first attempt to build a robust pdf extractor. Any comment/suggestion/feature request is welcome!**

### Installation
You can install this library by running the command:
```
pip install git+https://github.com/danielecastellana22/tyrannotext.git@main
```

### TODO:
- detect and discard footnotes
- improve text organisation when text is justified
- auto-detext if the number of columns in the page
- detect if a PDF is made by images and process it by using a OCR

