from .utils import eprint
from pymupdf import Rect, Point


# percentage tolerance
ORIGIN_TOL = 0.01
FONT_TOL = 0.02
ALIGNMENT_TOL = 0.1
#
N_CHAR_DIST = 4
N_LINE_DIST = 0.8  # number of lines to check if it is the same paragraph


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

    def has_almost_the_same_font_size(self, other: 'MyTextNode') -> bool:
        return (abs(self.font_size - other.font_size) / self.font_size) < FONT_TOL

    @property
    def text(self):
        return self.__text__

    def __repr__(self):
        return f'{self.text} at {self.bbox}'


class MySpan(MyTextNode):

    # lines is a list of spans
    def __init__(self, bbox: tuple, font_size: float, text: str, origin: tuple):
        super(MySpan, self).__init__(bbox, font_size, text)
        self.origin = Point(origin)
        self.avg_char_width = self.width / len(self.__text__)

    @classmethod
    def create_from_span_dict(cls, span_dict):
        t = span_dict['text'].strip()
        fs = span_dict['size']
        bbox = span_dict['bbox']
        origin = span_dict['origin']
        if len(t) > 0:
            return cls(bbox, fs, t, origin)
        else:
            return None


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

    def merge_line(self, other):
        for s in other.__children__:
            self.append_span(s)

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

    def is_almost_on_the_same_column(self, other: MyLine):
        same_col_left_align_score = (abs(self.bbox.x0 - other.bbox.x0) / self.width) # x0 should be the same
        same_col_right_align_score = (abs(self.bbox.x1 - other.bbox.x1) / self.width)  # x1 should be the same
        mid_point_1 = self.bbox.x0 + self.width / 2
        mid_point_2 = other.bbox.x0 + other.width / 2
        same_col_center_align_score = (abs(mid_point_2 - mid_point_1) / self.width)  # midpoint should be the same
        best_score = min(same_col_left_align_score, same_col_center_align_score, same_col_right_align_score)
        return best_score < ALIGNMENT_TOL

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

    def contains(self, other):
        return self.bbox.contains(other.bbox)

    def merge_inner_paragraph(self, other):
        assert self.contains(other)
        for l2 in other.__children__:
            found = False
            for l1 in self.__children__:
                if l2.is_almost_on_the_same_line(l1):
                    l1.merge_line(l2)
                    found = True
                    break
            if not found:
                eprint('Added new line when to merge an inner paragraph!')
                self.append_line(l2)

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

    '''
    def create_paragraph_from_list_of_lines(lines: list):
        lines.sort(key=lambda el: el.bbox.y0)
        remaining_lines = lines.copy()
        p = MyParagraph(remaining_lines.pop(0))

        while True:
            # find all the lines that are close vertically with the same font size
            remaining_lines.sort(key=lambda el: el.bbox.y0)
            lines_close_vertically = []
            i = 0
            while i < len(remaining_lines):
                l = remaining_lines[i]
                if p.is_close_vertically(l) and p.has_almost_the_same_font_size(l) and p.get_same_column_score(l) < 0.1:
                    remaining_lines.pop(i)
                    lines_close_vertically.append(l)
                else:
                    i += 1

            if len(lines_close_vertically) > 0:
                # among all the lines close vertically, find the one that is most aligned
                lines_close_vertically.sort(key=lambda el: p.get_same_column_score(el))
                p.append_line(lines_close_vertically[0])
                remaining_lines += lines_close_vertically[1:]
            else:
                break

        return p, remaining_lines
    '''

class MyPage:
    # TODO: discar pages with not so many words
    # TODO: detect and discard footnotes in pages
    # TODO: detect if a PDF is made by images and call a OCR to retrieve the text

    N_LINE_FOOTER_MARGIN = 5

    def __init__(self, page_dict):

        # 1) we trasform each span dict as TextElement object
        spans = []
        for b in page_dict['blocks']:
            for l in b['lines']:
                for s in l['spans']:
                    my_s = MySpan.create_from_span_dict(s)
                    if my_s is not None and len(my_s.text)>0:
                        spans.append(my_s)

        # 2) Create Lines: We cluster text elements that are on the same line and with not so many horizonalt space
        lines = []
        while len(spans) > 0:
            l, spans = MyLine.create_line_from_list_of_spans(spans)
            lines.append(l)

        # 3) Create Paragraph: We cluster text element that are in the same column,
        # closer vertically and have the same font size
        paragraphs = []
        while len(lines) > 0:
            p, lines = MyParagraph.create_paragraph_from_list_of_lines(lines)
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

        # 5) sort the remaining text elements vertically and horizontally
        paragraphs.sort(key=lambda el: (el.bbox.y0, el.bbox.x0))
        for p in paragraphs:
            p.sort()

        self.paragraphs = paragraphs
        self.bbox = Rect(0, 0, page_dict['width'], page_dict['height'])

        # TODO: do we have to consider also distance from the previous paragraph in the text?
        #self.remove_footers()

    def __is_near_the_bottom__(self, p: MyParagraph):
        if (self.bbox.y1 - p.bbox.y1) / p.avg_line_height < self.N_LINE_FOOTER_MARGIN:
            return True
        else:
            return False

    def remove_footers(self):
        i = 0
        while i < len(self.paragraphs):
            if self.__is_near_the_bottom__(self.paragraphs[i]):
                self.paragraphs.pop(i)
            else:
                i+=1

    def remove_headers(self):
        pass

    def get_text(self):
        return '\n'.join([el.text for el in self.paragraphs])