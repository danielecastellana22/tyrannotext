import pymupdf
from .dom import TyrannoPage
from .utils import eprint
from .configs import *


__all__ = ['TyrannoDocument', 'TyrannoSection']


class TyrannoDocument:

    def __init__(self, pdf_path, config: SimpleConfig = None, discard_pages_with_few_words=True, page_idxs=None):
        if config is None:
            config = SimpleConfig()

        self.sections_list = []

        doc = pymupdf.open(pdf_path)
        n_empty_pages = 0
        n_pages = 0
        n_pages_discarded = 0

        for idx_pag, page in enumerate(doc):
            n_pages += 1
            if page_idxs is not None and idx_pag not in page_idxs:
                continue
            txt_page = page.get_textpage()
            page_dict = txt_page.extractDICT(sort=True)
            if len(page_dict['blocks']) == 0:
                # TODO: try OCR
                # txt_page = page.get_textpage_ocr()
                # page_dict = txt_page.extractDICT(sort=True)
                n_empty_pages += 1
            else:
                pp = TyrannoPage.create_page_from_page_dict(page_dict, config)
                if pp is not None and (not discard_pages_with_few_words or pp.contains_enough_text()):
                    if len(self.sections_list) == 0:
                        self.sections_list.append(TyrannoSection(pp))
                    else:
                        if not self.sections_list[-1].add_page(pp):
                            self.sections_list.append(TyrannoSection(pp))
                else:
                    n_pages_discarded += 1
        doc.close()

        self.stats = {'n_pages': n_pages,
                      'n_empty_pages': n_empty_pages,
                      'n_pages_discarded': n_pages_discarded}

        if n_empty_pages / n_pages > 0.5:
            eprint(f'Warining: file {pdf_path} contains more than 50% of empty pages. Is it a image-based pdf?')

        self._text = "\n\n".join([s.get_text() for s in self.sections_list])

    def get_text(self):
        return self._text


class TyrannoSection:

    def __init__(self, page: TyrannoPage):
        self.pages = [page]
        self.title = page.title
        self.title_font_size = page.title_font_size

    def add_page(self, page: TyrannoPage):
        if self.title is None:
            return False

        if page.title is None or page.title_font_size < self.title_font_size:
            self.pages.append(page)
            return True

        return False

    def get_text(self):

        return '\n\n'.join([p.get_text() for p in self.pages])


