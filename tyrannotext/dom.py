from .utils import eprint
from pymupdf import Rect, Point
import statistics

__all__ = ['TyrannoTextNode', 'TyrannoSpan', 'TyrannoLine', 'TyrannoParagraph', 'TyrannoPage']


def almost_same_font_size(fs1, fs2, font_tol):
    return (abs(fs1-fs2) / fs2) < font_tol


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
        self._inner_sort()
        # TODO: keep elements already sorted with a binary tree

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
        return almost_same_font_size(other.font_size, self.font_size, self.config.font_tol)

    def is_almost_on_the_same_column(self, other: 'TyrannoTextNode')  -> bool:
        same_col_left_align_score = (abs(self.bbox.x0 - other.bbox.x0) / self.width) # x0 should be the same
        same_col_right_align_score = (abs(self.bbox.x1 - other.bbox.x1) / self.width)  # x1 should be the same
        mid_point_1 = self.bbox.x0 + self.width / 2
        mid_point_2 = other.bbox.x0 + other.width / 2
        same_col_center_align_score = (abs(mid_point_2 - mid_point_1) / self.width)  # midpoint should be the same
        best_score = min(same_col_left_align_score, same_col_center_align_score, same_col_right_align_score)
        return best_score < self.config.alignment_tol

    def is_almost_on_the_same_row(self, other: 'TyrannoTextNode')  -> bool:
        same_row_top_align_score = (abs(self.bbox.y0 - other.bbox.y0) / self.height) # x0 should be the same
        same_row_bottom_align_score = (abs(self.bbox.y1 - other.bbox.y1) / self.height)  # x1 should be the same
        mid_point_1 = self.bbox.y0 + self.height / 2
        mid_point_2 = other.bbox.y0 + other.height / 2
        same_row_middle_align_score = (abs(mid_point_2 - mid_point_1) / self.height)  # midpoint should be the same
        best_score = min(same_row_top_align_score, same_row_middle_align_score, same_row_bottom_align_score)
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

    def __iter__(self):
        for c in self._children:
            yield c


class TyrannoSpan(TyrannoTextNode):

    # lines is a list of spans
    def __init__(self, bbox: tuple, font_size: float, text: str, origin: tuple, config):
        super(TyrannoSpan, self).__init__(bbox, font_size, text, config=config)
        self.origin = Point(origin)
        self.avg_char_width = self.width / len(self._text)

    @classmethod
    def create_from_span_dict(cls, span_dict, config):
        t = span_dict['text'].strip()
        is_all_non_ascii = True
        for i in range(len(t)):
            if t[i:i+1].isascii():
                is_all_non_ascii = False
                break
        if is_all_non_ascii:
            return None
        fs = int(span_dict['size'])
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

    @property
    def origin(self):
        return self._children[0].origin

    def is_almost_on_the_same_line(self, other: TyrannoSpan) -> float:
        return (abs(self.origin.y - other.origin.y) / self.height) < self.config.origin_tol

    def is_close_horizontally(self, other: TyrannoSpan):
        return (self.get_horizontal_distance(other) / self.avg_char_width) < self.config.n_char_dist

    def is_a_span_to_merge(self, other: TyrannoSpan):
        return (self.is_almost_on_the_same_line(other)
                and self.is_close_horizontally(other)
                and self.has_almost_the_same_font_size(other))

    def append_span(self, new_span: TyrannoSpan) -> None:
        self._append_child(new_span)
        # update the average
        n_child = len(self._children)
        self.avg_char_width = (self.avg_char_width * (n_child-1) + new_span.avg_char_width) / n_child

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

    @staticmethod
    def create_list_of_lines_from_list_of_spans(spans: list):
        spans.sort(key=lambda el: el.bbox.x0)
        lines_list = []

        while len(spans) > 0:

            l = TyrannoLine(spans.pop(0))

            found = True
            while found:
                found = False
                s = None
                for s in spans:
                    if l.is_a_span_to_merge(s):
                        found = True
                        break

                if found:
                    l.append_span(s)
                    spans.remove(s)

            lines_list.append(l)

        return lines_list


class TyrannoParagraph(TyrannoTextNode):

    def __init__(self, first_line: TyrannoLine):
        super(TyrannoParagraph, self).__init__(first_child=first_line)
        self.font_size = first_line.font_size
        self.col_id = None

    def is_close_vertically(self, other: TyrannoLine):
        return (abs(self._children[-1].origin.y - other.origin.y) / self.font_size) < self.config.n_line_dist

    def is_a_line_to_merge(self, other: TyrannoLine):
        return (self.is_close_vertically(other)
                and self.has_almost_the_same_font_size(other)
                and self.is_almost_on_the_same_column(other))

    def append_line(self, new_line: TyrannoLine):
        self._append_child(new_line)

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

    @staticmethod
    def create_list_of_paragraph_from_list_of_lines(lines: list):
        lines.sort(key=lambda el: el.bbox.y0)
        par_list = []

        while len(lines) > 0:

            p = TyrannoParagraph(lines.pop(0))

            found = True
            while found:
                found = False
                l = None
                for l in lines:
                    if p.is_a_line_to_merge(l):
                        found = True
                        break

                if found:
                    p.append_line(l)
                    lines.remove(l)

            par_list.append(p)

        return par_list


class TyrannoPage:

    def __init__(self, paragraphs, bbox, config):
        self.bbox = bbox

        # counting the number of spans for each font size
        font_size_counts = {}
        for p in paragraphs:
            for l in p:
                for s in l:
                    # update font counting
                    v = font_size_counts.setdefault(s.font_size, 0)
                    font_size_counts[s.font_size] = v + 1
        max_font_size = max(font_size_counts.keys())
        most_freq = max(font_size_counts.values())
        most_freq_font_size = [k for k in font_size_counts if font_size_counts[k] == most_freq][0]

        title = None
        title_font_size = None
        if almost_same_font_size(paragraphs[0].font_size, max_font_size, config.font_tol) and paragraphs[0].font_size > most_freq_font_size:
            title = paragraphs[0].get_text()
            title_font_size = max_font_size
            paragraphs.pop(0)

        self.paragraphs = paragraphs
        self.title = title
        self.title_font_size = title_font_size



    @staticmethod
    def create_page_from_page_dict(page_dict: dict, config):

        # 1) we trasform each span dict as TextElement object
        spans = []
        for b in page_dict['blocks']:
            for l in b['lines']:
                for s in l['spans']:
                    my_s = TyrannoSpan.create_from_span_dict(s, config)
                    if my_s is not None and len(my_s.get_text()) > 0 and my_s.width > 0.01:
                        spans.append(my_s)

        if len(spans) == 0:
            return None

        # 2) Create Lines: We cluster text elements that are on the same line and with not so many horizonalt space
        lines = TyrannoLine.create_list_of_lines_from_list_of_spans(spans)

        # 3) Create Paragraph: We cluster text element that are in the same column,
        # that are close vertically and have the same font size
        paragraphs = TyrannoParagraph.create_list_of_paragraph_from_list_of_lines(lines)

        # TODO: 4) check if there are paragraph with one inside the other:

        # 5) sort paragraph according to page layout (i.e. the columns)
        paragraphs.sort(key=lambda el: (el.bbox.x0, el.bbox.y0))
        for p in paragraphs:
            p.rec_sort()

        col_list = []
        while len(paragraphs) > 0:

            curr_p = paragraphs.pop(0)
            on_same_col = []
            for p in paragraphs:
                # check if p is on right of curr_p
                if curr_p.is_almost_on_the_same_column(p):
                    on_same_col.append(p)

            for p in on_same_col:
                paragraphs.remove(p)

            on_same_col.insert(0, curr_p)
            col_list.append(on_same_col)

        paragraphs = []
        all_font_sizes = set()
        for c in col_list:
            for p in c:
                paragraphs.append(p)
                all_font_sizes.add(p.font_size)

        # 6) remove footnotes
        # TODO: detect and discard footnotes in pages

        # 7) build the page
        return TyrannoPage(paragraphs, Rect(0, 0, page_dict['width'], page_dict['height']), config)

    def get_text(self):
        s = ''
        if self.title is not None:
            s += self.title + '\n'
        s += '\n'.join([p.get_text() for p in self.paragraphs])
        return s

    def contains_enough_text(self):
        text_in_page = self.get_text()

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
        return number_of_letters / len(text_in_page) > 0.5
