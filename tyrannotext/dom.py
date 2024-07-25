from .utils import eprint
from pymupdf import Rect, Point

__all__ = ['TyrannoTextNode', 'TyrannoSpan', 'TyrannoLine', 'TyrannoParagraph', 'TyrannoPage']


class TyrannoTextNode:

    def __init__(self, bbox: tuple = None, font_size: float = None, text: str = None,
                 first_child: 'TyrannoTextNode' = None, config=None):
        if first_child is not None:
            if bbox is not None or font_size is not None or text is not None or config is not None:
                raise ValueError('If first_child is specified, the other arguments must be None!')
            self.config = first_child.config
            self.bbox = Rect(first_child.bbox)
            self.font_size = first_child.font_size
            self._text = None
            self._children = [first_child]
        else:
            if bbox is None or font_size is None or text is None or config is None:
                raise ValueError('If first_child is None, the other arguments must be specified!')
            self.config = config
            self.bbox = Rect(bbox)
            self.font_size = font_size
            self._text = text
            self._children = []

    @property
    def width(self) -> float:
        return self.bbox.width

    @property
    def height(self) -> float:
        return self.bbox.height

    def _append_child(self, new_child: 'TyrannoTextNode', allow_different_fonts: bool = False):
        if not allow_different_fonts and not self.has_almost_the_same_font_size(new_child):
            eprint("We are merging text elements with different font sizes! Are you sure?")
        self.bbox.include_rect(new_child.bbox)
        self._children.append(new_child)

    def get_vertical_distance(self, other: 'TyrannoTextNode') -> float:
        if self.bbox.y1 <= other.bbox.y0:
            return other.bbox.y0 - self.bbox.y1
        elif other.bbox.y1 <= self.bbox.y0:
            return self.bbox.y0 - other.bbox.y1
        else:
            return -1  # they are overlapped

    def get_horizontal_distance(self, other: 'TyrannoTextNode') -> float:
        if self.bbox.x1 <= other.bbox.x0:
            return other.bbox.x0 - self.bbox.x1
        elif other.bbox.x1 <= self.bbox.x0:
            return self.bbox.x0 - other.bbox.x1
        else:
            return -1  # they are overlapped

    def has_almost_the_same_font_size(self, other: 'TyrannoTextNode') -> bool:
        return (abs(self.font_size - other.font_size) / self.font_size) < self.config.font_tol

    def is_almost_on_the_same_column(self, other: 'TyrannoTextNode')  -> bool:
        same_col_left_align_score = (abs(self.bbox.x0 - other.bbox.x0) / self.width) # x0 should be the same
        same_col_right_align_score = (abs(self.bbox.x1 - other.bbox.x1) / self.width)  # x1 should be the same
        mid_point_1 = self.bbox.x0 + self.width / 2
        mid_point_2 = other.bbox.x0 + other.width / 2
        same_col_center_align_score = (abs(mid_point_2 - mid_point_1) / self.width)  # midpoint should be the same
        best_score = min(same_col_left_align_score, same_col_center_align_score, same_col_right_align_score)
        return best_score < self.config.alignment_tol

    def contains(self, other: 'TyrannoTextNode') -> bool:
        return self.bbox.contains(other.bbox)

    def _inner_sort(self):
        pass

    def rec_sort(self):
        self._inner_sort()
        if self._children:
            for el in self._children:
                el.rec_sort()

    def get_text(self):
        raise NotImplementedError('Should be implemented in the sub-class')

    def __repr__(self):
        return f'{self.get_text()} at {self.bbox}'


class TyrannoSpan(TyrannoTextNode):

    # lines is a list of spans
    def __init__(self, bbox: tuple, font_size: float, text: str, origin: tuple, config):
        super(TyrannoSpan, self).__init__(bbox, font_size, text, config=config)
        self.origin = Point(origin)
        self.avg_char_width = self.width / len(self._text)

    @classmethod
    def create_from_span_dict(cls, span_dict, config):
        t = span_dict['text'].strip()
        fs = span_dict['size']
        bbox = span_dict['bbox']
        origin = span_dict['origin']
        if len(t) > 0:
            return cls(bbox, fs, t, origin, config)
        else:
            return None

    def get_text(self):
        return self._text.encode('utf-8', 'ignore').decode('utf-8')


class TyrannoLine(TyrannoTextNode):

    def __init__(self, first_span: TyrannoSpan):
        # we copy all the properties of first_span
        super(TyrannoLine, self).__init__(first_child=first_span)
        self.avg_char_width = first_span.avg_char_width
        self.origin = Point(first_span.origin)

    def is_almost_on_the_same_line(self, other: TyrannoSpan) -> float:
        return (abs(self.origin.y - other.origin.y) / self.height) < self.config.origin_tol

    def is_close_horizontally(self, other: TyrannoSpan):
        return (self.get_horizontal_distance(other) / self.avg_char_width) < self.config.n_char_dist

    def append_span(self, new_span: TyrannoSpan) -> None:
        self._append_child(new_span)
        # update the average
        n_child = len(self._children)
        self.avg_char_width = (self.avg_char_width * (n_child-1) + new_span.avg_char_width) / n_child

    @staticmethod
    def create_line_from_list_of_spans(spans: list):
        spans.sort(key=lambda el: el.bbox.x0)
        l = TyrannoLine(spans[0])
        # try to merge vertically
        remaining_spans = []
        for s in spans[1:]:
            if l.is_almost_on_the_same_line(s) and l.is_close_horizontally(s) and l.has_almost_the_same_font_size(s):
                l.append_span(s)
            else:
                remaining_spans.append(s)
        return l, remaining_spans

    def _inner_sort(self):
        self._children.sort(key=lambda el: el.bbox.x0)

    def get_text(self):
        s = ''
        for el in self._children:
            if not s:
                s = el.get_text()
            else:
                s += (' ' if s[-1] != ' ' else '') + el.get_text()
        return s.strip()

    '''
        def merge_line(self, other: 'TyrannoLine'):
            for s in other._children:
                self.append_span(s)
    '''


class TyrannoParagraph(TyrannoTextNode):

    def __init__(self, first_line: TyrannoLine):
        super(TyrannoParagraph, self).__init__(first_child=first_line)
        self.avg_line_height = first_line.height

    def is_close_vertically(self, other: TyrannoLine):
        return (self.get_vertical_distance(other) / self.avg_line_height) < self.config.n_line_dist

    def append_line(self, new_line: TyrannoLine):
        self._append_child(new_line)
        # update the average
        n_child = len(self._children)
        self.avg_line_height = self.height / n_child

    @staticmethod
    def create_paragraph_from_list_of_lines(lines: list):
        lines.sort(key=lambda el: el.bbox.y0)
        p = TyrannoParagraph(lines[0])
        # try to merge vertically
        remaining_lines = []
        for l in lines[1:]:
            if p.is_close_vertically(l) and p.has_almost_the_same_font_size(l) and p.is_almost_on_the_same_column(l):
                p.append_line(l)
            else:
                remaining_lines.append(l)
        return p, remaining_lines

    def _inner_sort(self):
        self._children.sort(key=lambda el: el.bbox.y0)

    def get_text(self):
        s = None
        for el in self._children:
            if not s:
                s = el.get_text()
            elif s[-1] == '-':
                s = s[:-1] + el.get_text()
            elif s[-1] != ' ':
                s += ' ' + el.get_text()
            else:
                s += el.get_text()
        return s

    '''
        def merge_inner_paragraph(self, other):
            assert self.contains(other)
            for l2 in other._children:
                found = False
                for l1 in self._children:
                    if l2.is_almost_on_the_same_line(l1):
                        l1.merge_line(l2)
                        found = True
                        break
                if not found:
                    eprint('Added new line when to merge an inner paragraph!')
                    self.append_line(l2)
    '''


class TyrannoColumn(TyrannoTextNode):

    def __init__(self, first_line: TyrannoParagraph):
        super(TyrannoColumn, self).__init__(first_child=first_line)

    def append_paragraph(self, new_paragraph: TyrannoParagraph):
        self._append_child(new_paragraph, allow_different_fonts=True)

    @staticmethod
    def create_column_from_list_of_paragraphs(paragraphs: list):
        paragraphs.sort(key=lambda el: (el.bbox.x0, el.bbox.y0))
        c = TyrannoColumn(paragraphs[0])
        # try to merge vertically
        remaining_paragraphs = []
        for p in paragraphs[1:]:
            if c.is_almost_on_the_same_column(p):
                c.append_paragraph(p)
            else:
                remaining_paragraphs.append(p)
        return c, remaining_paragraphs

    def _inner_sort(self):
        self._children.sort(key=lambda el: el.bbox.y0)

    def get_text(self):
        # TODO: this breaks when a text is splitted between two columns
        return '\n'.join([el.get_text() for el in self._children])


class TyrannoPage:
    # TODO: discard pages with not so many words
    # TODO: detect and discard footnotes in pages
    # TODO: detect if a PDF is made by images and call a OCR to retrieve the text

    def __init__(self, page_dict, config):

        self.config = config

        # 1) we trasform each span dict as TextElement object
        spans = []
        for b in page_dict['blocks']:
            for l in b['lines']:
                for s in l['spans']:
                    my_s = TyrannoSpan.create_from_span_dict(s, config)
                    if my_s is not None and len(my_s.get_text()) > 0 and my_s.width > 0.01:
                        spans.append(my_s)

        # 2) Create Lines: We cluster text elements that are on the same line and with not so many horizonalt space
        lines = []
        while len(spans) > 0:
            l, spans = TyrannoLine.create_line_from_list_of_spans(spans)
            lines.append(l)

        # 3) Create Paragraph: We cluster text element that are in the same column,
        # that are close vertically and have the same font size
        paragraphs = []
        while len(lines) > 0:
            p, lines = TyrannoParagraph.create_paragraph_from_list_of_lines(lines)
            paragraphs.append(p)

        # # 4) check if there are paragraph with one inside the other:
        # if yes, force to merge it by understanding where the text goes
        # (this helps in case of justified text with a lot of space that is not merged in step 2)
        # IT COULD BE A PROBLEM WITH FLOATING TEXT LIKE CAPTION
        '''
        i=0
        while i < len(paragraphs):
            j=i+1
            while j < len(paragraphs):
                if paragraphs[i].contains(paragraphs[j]):
                    paragraphs[i].merge_inner_paragraph(paragraphs[j])
                    paragraphs.pop(j)
                else:
                    j+=1
            i+=1
        '''

        # 5) create columns: we cluster paragraph in the same column
        self.columns = []
        while len(paragraphs) > 0:
            c, paragraphs = TyrannoColumn.create_column_from_list_of_paragraphs(paragraphs)
            self.columns.append(c)

        # 6) sort the remaining text elements vertically and horizontally
        self.columns.sort(key=lambda el: (el.bbox.y0, el.bbox.x0))
        for c in self.columns:
            c.rec_sort()

        self.bbox = Rect(0, 0, page_dict['width'], page_dict['height'])

        # TODO: do we have to consider also distance from the previous paragraph in the text?
        #self.remove_footers()

    def get_text(self):
        return '\n'.join([el.get_text() for el in self.columns])

    '''
        def __is_near_the_bottom(self, p: TyrannoParagraph):
            if (self.bbox.y1 - p.bbox.y1) / p.avg_line_height < self.config.n_line_footer_margin:
                return True
            else:
                return False

        def remove_footers(self):
            i = 0
            while i < len(self.columns):
                if self.__is_near_the_bottom(self.columns[i]):
                    self.columns.pop(i)
                else:
                    i+=1

        def remove_headers(self):
            pass
        '''