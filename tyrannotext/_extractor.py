import pymupdf4llm
from ._utils import eprint
from marko.ext.gfm import gfm
from marko.ext.gfm.elements import *
from marko.block import *
from marko.inline import *
from marko.element import Element


__all__ = ['TyrannoDocument', 'TyrannoSection', 'to_markdown']


def to_markdown(pdf_path, *args, **kwargs):
    return pymupdf4llm.to_markdown(pdf_path, *args, **kwargs, page_chunks=False)


class TyrannoDocument:

    def __init__(self, md_string):

        self.stats = {'n_pages': 0,
                      'n_sections': 0}
        self.root = TyrannoSection('root', 0)

        curr_section = self.root

        parsed_md = gfm.parse(md_string)
        for el in parsed_md.children:
            if isinstance(el, Heading):
                # we create a new section
                new_title = el.children[0].children
                if curr_section.title != new_title:
                    self.root.add_section(curr_section)
                    curr_section = TyrannoSection(new_title, el.level)
            if isinstance(el, ThematicBreak):
                self.stats['n_pages'] += 1
            else:
                # we add the element to the current section
                curr_section.add_element(el)

        # count sections
        s = self.root
        while len(s.subsections) == 1:
            s = s.subsections[0]
        self.stats['n_sections'] += len(s.subsections)

    def get_plain_text(self):
        return self.root.get_plain_text()


class TyrannoSection:

    def __init__(self, title, level):
        self.title = title
        self.level = level
        self.subsections = []
        self.tables = []
        self.images = []
        self.graphics = []
        self.text = ''

    def add_section(self, new_section: 'TyrannoSection'):
        if self.level >= new_section.level:
            return False
        if len(self.subsections) == 0 or not self.subsections[-1].add_section(new_section):
            self.subsections.append(new_section)
        return True

    def add_element(self, el: Element):
        if isinstance(el, BlankLine) or isinstance(el, ThematicBreak):
            pass
        elif isinstance(el, Table):
            self._add_table(el)
        elif isinstance(el, Image):
            # TODO: add image?
            pass
        else:
            self._add_text(el)

    def _add_table(self, table_el):
        pass

    def _add_text(self, text_el):
        if isinstance(text_el.children, str):
            t = text_el.children.strip()
            if len(t) > 0:
                self.text += ' ' + t
        else:
            if isinstance(text_el, List):
                self.text += '\n' + text_el.bullet

            for child in text_el.children:
                self._add_text(child)

    def __repr__(self):
        return f'{self.title}'

    def get_plain_text(self, exclude_title=False):
        plain_text = f'{self.title}\n' if not exclude_title else ''
        plain_text += f'{self.text}\n'
        rec_string = '\n'.join([s.get_plain_text(exclude_title) for s in self.subsections])
        plain_text += f'{rec_string}\n'
        return plain_text