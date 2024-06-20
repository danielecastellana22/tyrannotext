import sys

import stanza
from pypdf import PdfReader
import re
import spacy

from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer, LTChar, LTRect, LTFigure
from symspellpy import SymSpell, Verbosity
import unicodedata
# layout ml to exact number on table document question
# extration summary per estrazione dati frasi dati utili clustering


class MyPDFExtractor:

    def __init__(self, pipeline_config=None):
        if not pipeline_config:
            pipeline_config = {'lang': 'it', 'processors': 'tokenize'}
        self.nlp_stanza = stanza.Pipeline(**pipeline_config)
        self.nlp_spacy = spacy.load('it_core_news_lg', exclude=["tok2vec", "morphologizer", "tagger", "parser", "lemmatizer",
                                                          "attribute_ruler", "ner"] )

        sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7, count_threshold=5)
        dictionary_path = 'preprocessing/repubblica_unigrams.txt'
        #'preprocessing/it-100k.txt'
        #'preprocessing/repubblica_unigrams.txt'
        #"preprocessing/sorted.it.word.unigrams"
        # term_index is the column of the term and count_index is the
        # column of the term frequency
        sym_spell.load_dictionary(dictionary_path, term_index=1, count_index=0, separator='\t', encoding='ISO-8859-1')
        self.sym_spell = sym_spell

    def __recover_spelling__(self, w):
        w = unicodedata.normalize('NFKC', w)
        if len(w) <= 2 or w.isalpha() or w.isnumeric() or w[-1] == "'" or w[-1] == '’' or w[-2] == "," or w[-3] == ",":
            return w

        word_to_search = ''
        for c in w:
            if c.isalpha():
                word_to_search += c
            else:
                word_to_search += 'ti'
        suggestions = self.sym_spell.lookup(word_to_search, Verbosity.CLOSEST, transfer_casing=True)
        if len(suggestions) > 0:
            return suggestions[0].term

        return w

    def __spacy_tokenize_text__(self, text):
        doc = self.nlp_spacy(text)
        word_list = []
        for w in doc:
            word_list.append(self.__recover_spelling__(w.__text__))

        return word_list

    def __tokenize_text__(self, text):
        doc = self.nlp_stanza(text)
        sent_list = []

        for s in doc.sentences:
            word_list = []

            for w in self.nlp_spacy(s.__text__):
                if not w.is_space:
                    word_list.append(self.__recover_spelling__(w.__text__))
            sent_list.append(' '.join(word_list))

        return sent_list

    def __is_a_page_with_text__(self, text_in_page: str):
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

    def extract_text_from_pdf(self, pdf_path):
        doc_text = ''
        for pagenum, page in enumerate(extract_pages(pdf_path)):
            # Iterate the elements that composed a page
            page_text = ''
            for element in page:
                aa = 3
                # Check if the element is a text element
                if isinstance(element, LTTextContainer):
                    #t = element.get_text().replace('\n', ' ').replace('  ', ' ').replace('   ', ' ').strip()
                    t = element.get_text().replace('\n', ' ').strip()
                    if len(t) >= 10:
                        page_text += t
                        if page_text[-1] != '-':
                            page_text += ' '
                        else:
                            page_text = page_text[:-1]

            if self.__is_a_page_with_text__(page_text):
                doc_text += page_text

        return '\n'.join(self.__tokenize_text__(doc_text))
