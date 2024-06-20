import pymupdf
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer
from pdfminer.layout import LAParams
from tyrannotext.dom import MyPage

if __name__ == '__main__':

    id_file = '4_74'
    fname = f"data/{id_file}.pdf" # get document filename
    outname = f'data/{id_file}.txt'
    doc = pymupdf.open(fname)
    with open(outname, 'w', encoding='UTF-8') as fout:
        for page in doc:
            txt_page = page.get_textpage()
            page_dict = txt_page.extractDICT(sort=True)
            pp = MyPage(page_dict)
            fout.write(pp.get_text() + "\n\n")
    doc.close()

    # write as a binary file to support non-ASCII characters
    #pathlib.Path(fname + ".txt").write_bytes(text.encode())
    #for pagenum, page in enumerate(extract_pages(fname, laparams=LAParams(line_margin=0))):
    #    # Iterate the elements that composed a page
    #    page_text = []
    #    for element in page:
    #        aa = 3
    #        # Check if the element is a text element
    #        if isinstance(element, LTTextContainer):
    #            # t = element.get_text().replace('\n', ' ').replace('  ', ' ').replace('   ', ' ').strip()
    #            paragraph_text = element.get_text().replace('\n', ' ').strip().replace('- ', '')
    #            page_text.append(paragraph_text)