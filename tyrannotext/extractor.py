import pymupdf
from .dom import MyPage


class MyPDFExtractor:

    # TODO: use init to setup some values (LINE_DIST, etc..)

    def extract_text_from_pdf(self, pdf_path):
        doc = pymupdf.open(pdf_path)
        s = ''
        for page in doc:
            txt_page = page.get_textpage()
            page_dict = txt_page.extractDICT(sort=True)
            pp = MyPage(page_dict)
            s += pp.get_text() + "\n\n"
        doc.close()
        return s
