from ..reader import DataCiteReader
from ..format import format_value


class PangaeaDatacite(DataCiteReader):
    def update(self, doc):
        # doc.discipline = format_value(self.parser.find('subject'), type='string_words', one=True).split(' ')[0]
        pass
