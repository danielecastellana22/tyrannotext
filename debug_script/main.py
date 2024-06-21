from tyrannotext.extractor import MyPDFExtractor

if __name__ == '__main__':

    id_file = '4_74'
    fname = f"data/{id_file}.pdf" # get document filename
    outname = f'data/{id_file}.txt'
    my_extractor = MyPDFExtractor()
    with open(outname, 'w', encoding='UTF-8') as fout:
        fout.write(my_extractor.extract_text_from_pdf(fname))