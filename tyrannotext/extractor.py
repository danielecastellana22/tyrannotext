import pymupdf
from .dom import MyPage
import os
from .utils import eprint

class MyPDFExtractor:

    # TODO: use init to setup some values (LINE_DIST, etc..)
    def __init__(self, discard_pages_with_few_words=True):
        self.discard_pages_with_few_words = discard_pages_with_few_words

    def extract_text_from_pdf(self, pdf_path):
        doc = pymupdf.open(pdf_path)
        s = ''
        n_empty_pages = 0
        n_pages = 0
        for page in doc:
            n_pages += 1
            txt_page = page.get_textpage()
            page_dict = txt_page.extractDICT(sort=True)
            if len(page_dict['blocks']) == 0:
                # TODO: try OCR
                #txt_page = page.get_textpage_ocr()
                #page_dict = txt_page.extractDICT(sort=True)
                n_empty_pages +=1
            else:
                pp = MyPage(page_dict)
                page_text = pp.get_text()
                if not self.discard_pages_with_few_words or self.__is_a_page_with_text(page_text):
                    s += page_text + "\n\n"
        doc.close()
        if n_empty_pages / n_pages > 0.5:
            eprint(f'Warining: file {pdf_path} contains more than 50% of empty pages. Is it a image-based pdf?')
        return s

    def __is_a_page_with_text(self, text_in_page: str):
        if len(text_in_page) == 0:
            return False

        number_of_digits = 0
        number_of_letters = 0
        number_of_other_chars = 0
        for c in text_in_page:
            if c.isnumeric():
                number_of_digits += 1
            elif c.isalpha():
                number_of_letters += 1
            else:
                number_of_other_chars += 1

        # 0.5 could be improved
        return number_of_letters/len(text_in_page) > 0.5