from typing import Union
from .utils import eprint
from pymupdf import Rect, Point

# percentage tolerance
BBOX_TOL = 0.02
ORIGIN_TOL = 0.01
FONT_TOL = 0.02
#
N_CHAR_DIST = 4
N_LINE_DIST = 1.5


class MyTextNode:

    def __init__(self, bbox: tuple = None, font_size: float = None, text: str = None,
                 first_child: 'MyTextNode' = None):
        if first_child is not None:
            if bbox is not None or font_size is not None or text is not None:
                raise ValueError('If first_child is specified, the other arguments must be None!')
            self.bbox = Rect(first_child.bbox)
            self.font_size = first_child.font_size
            self.__text__ = None
            self.__children__ = [first_child]
        else:
            if bbox is None or font_size is None or text is None:
                raise ValueError('If first_child is None, the other arguments must be specified!')
            self.bbox = Rect(bbox)
            self.font_size = font_size
            self.__text__ = text
            self.__children__ = []

    @property
    def width(self) -> float:
        return self.bbox.width

    @property
    def height(self) -> float:
        return self.bbox.height

    def get_vertical_distance(self, other: 'MyTextNode') -> float:
        if self.bbox.y1 <= other.bbox.y0:
            return other.bbox.y0 - self.bbox.y1
        elif other.bbox.y1 <= self.bbox.y0:
            return self.bbox.y0 - other.bbox.y1
        else:
            return -1  # they are overlapped

    def get_horizontal_distance(self, other: 'MyTextNode') -> float:
        if self.bbox.x1 <= other.bbox.x0:
            return other.bbox.x0 - self.bbox.x1
        elif other.bbox.x1 <= self.bbox.x0:
            return self.bbox.x0 - other.bbox.x1
        else:
            return -1  # they are overlapped

    def is_almost_on_the_same_line(self, other: 'MyTextNode') -> float:
        same_line_top_align = (abs(self.bbox.y0 - other.bbox.y0) / self.width) < BBOX_TOL  # x0 should be the same
        same_line_bottom_align = (abs(self.bbox.y1 - other.bbox.y1) / self.width) < BBOX_TOL  # x1 should be the same
        mid_point_1 = self.bbox.y0 + self.width / 2
        mid_point_2 = other.bbox.y0 + other.width / 2
        same_line_center_align = (abs(mid_point_2 - mid_point_1) / self.width) < BBOX_TOL  # midpoint should be the same
        return same_line_top_align or same_line_center_align or same_line_bottom_align

    def is_almost_on_the_same_column(self, other: 'MyTextNode') -> float:
        same_col_left_align = (abs(self.bbox.x0 - other.bbox.x0) / self.width) < BBOX_TOL  # x0 should be the same
        same_col_right_align = (abs(self.bbox.x1 - other.bbox.x1) / self.width) < BBOX_TOL  # x1 should be the same
        mid_point_1 = self.bbox.x0 + self.width / 2
        mid_point_2 = other.bbox.x0 + other.width / 2
        same_col_center_align = (abs(mid_point_2 - mid_point_1) / self.width) < BBOX_TOL  # midpoint should be the same
        return same_col_left_align or same_col_center_align or same_col_right_align

    def has_almost_the_same_font_size(self, other: 'MyTextNode') -> bool:
        return (abs(self.font_size - other.font_size) / self.font_size) < FONT_TOL

    @property
    def text(self):
        return self.__text__

    def __repr__(self):
        return f'{self.text} at {self.bbox}'


class MySpan(MyTextNode):

    # lines is a list of spans
    def __init__(self, span_dict):
        super(MySpan, self).__init__(bbox=span_dict['bbox'], text=span_dict['text'], font_size=span_dict['size'])
        self.origin = Point(span_dict['origin'])
        self.avg_char_width = self.width / len(self.__text__)


class MyLine(MyTextNode):

    def __init__(self, first_span: MySpan):
        # we copy all the properties of first_span
        super(MyLine, self).__init__(first_child=first_span)
        self.avg_char_width = first_span.avg_char_width
        self.origin = Point(first_span.origin)

    def is_almost_on_the_same_line(self, other: MySpan) -> float:
        return (abs(self.origin.y - other.origin.y) / self.height) < ORIGIN_TOL

    def is_close_horizontally(self, other: MySpan):
        return (self.get_horizontal_distance(other) / self.avg_char_width) < N_CHAR_DIST

    def append_span(self, new_span: MySpan) -> None:
        if not self.has_almost_the_same_font_size(new_span):
            eprint("We are merging text elements with different font sizes! Are you sure?")
        self.bbox.include_rect(new_span.bbox)
        self.__children__.append(new_span)
        # update the average
        n_child = len(self.__children__)
        self.avg_char_width = (self.avg_char_width * (n_child-1) + new_span.avg_char_width) / n_child

    @property
    def text(self):
        s = ''
        for el in self.__children__:
            if not s:
                s = el.text
            else:
                s += (' ' if s[-1] != ' ' else '') + el.text
        return s.strip()

    def sort(self):
        self.__children__.sort(key=lambda el: el.bbox.x0)

    @staticmethod
    def create_line_from_list_of_spans(spans: list):
        spans.sort(key=lambda el: el.bbox.x0)
        l = MyLine(spans[0])
        # try to merge vertically
        remaining_spans = []
        for s in spans[1:]:
            if l.is_almost_on_the_same_line(s) and l.is_close_horizontally(s) and l.has_almost_the_same_font_size(s):
                l.append_span(s)
            else:
                remaining_spans.append(s)
        return l, remaining_spans


class MyParagraph(MyTextNode):

    def __init__(self, first_line: MyLine):
        super(MyParagraph, self).__init__(first_child=first_line)
        self.avg_line_height = first_line.height

    def is_close_vertically(self, other: MyLine):
        return (self.get_vertical_distance(other) / self.avg_line_height) < N_LINE_DIST

    def append_line(self, new_line: MyLine):
        if not self.has_almost_the_same_font_size(new_line):
            eprint("We are merging text elements with different font sizes! Are you sure?")
        self.bbox.include_rect(new_line.bbox)
        self.__children__.append(new_line)
        # update the average
        n_child = len(self.__children__)
        self.avg_line_height = self.height / n_child

    @property
    def text(self):
        s = None
        for el in self.__children__:
            if not s:
                s = el.text
            elif s[-1] == '-':
                s = s[:-1] + el.text
            elif s[-1] != ' ':
                s += ' ' + el.text
            else:
                s += el.text
        return s

    def sort(self):
        self.__children__.sort(key=lambda el: el.bbox.y0)
        for el in self.__children__:
            el.sort()

    @staticmethod
    def create_paragraph_from_list_of_lines(lines: list):
        lines.sort(key=lambda el: el.bbox.y0)
        p = MyParagraph(lines[0])
        # try to merge vertically
        remaining_lines = []
        for l in lines[1:]:
            if p.is_close_vertically(l) and p.has_almost_the_same_font_size(l) and p.is_almost_on_the_same_column(l):
                p.append_line(l)
            else:
                remaining_lines.append(l)
        return p, remaining_lines


class MyPage:
    # TODO: discar pages with not so many words
    # TODO: detect and discard footnotes in pages
    # TODO: detect if a PDF is made by images and call a OCR to retrieve the text


    def __init__(self, page_dict):
        #super(MyPage, self).__init__((0, 0, page_dict['width'], page_dict['height']))

        # 1) we trasform each span dict as TextElement object
        spans = []
        for b in page_dict['blocks']:
            for l in b['lines']:
                for s in l['spans']:
                    my_s = MySpan(s)
                    if my_s.width > 0:
                        spans.append(my_s)

        # 2) Create Lines: We cluster text elements that are on the same line and with not so many horizonalt space
        lines = []
        while len(spans) > 0:
            l, spans = MyLine.create_line_from_list_of_spans(spans)
            lines.append(l)

        # 3) Create Paragraph: We cluster text element that are in the same column, closer vertically and have the same font size
        paragraphs = []
        while len(lines) > 0:
            p, lines = MyParagraph.create_paragraph_from_list_of_lines(lines)
            paragraphs.append(p)

        # TODO: this helps in case of justified text with a lot of space that is not mere in step 2)
        # 4) check if there are paragraph with one inside the other
        # if yes, force to merge it by understanding where the text goes


        # 5) sort the remaining text elements vertically and horizontally
        # TODO: sort also on x0 if multiple columns
        paragraphs.sort(key=lambda el: el.bbox.y0)
        for p in paragraphs:
            p.sort()


        # 6) get the text
        self.text = '\n'.join([el.text for el in paragraphs])