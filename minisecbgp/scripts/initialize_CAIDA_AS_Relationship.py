import bz2


def main():
    zip_file = './CAIDA_AS_Relationship/20200201.as-rel2.txt.bz2'
    output_file = './CAIDA_AS_Relationship/20200201.as-rel2.txt'
    file = bz2.open(zip_file, 'rt')
    data = file.read()
    file = open(output_file, 'w+')
    file.write(data)
    file.close()
