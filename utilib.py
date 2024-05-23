class EncDec():
    encode_list = ['utf-8',
                   'Windows-1251']
    enc = encode_list[0]
    err = 'replace'

    def get_codelist(self):
        return self.encode_list

    def set_enc(self,index):
        if index == 0:
            self.err = 'replace'
            self.enc = self.encode_list[0]
        else:
            self.err = 'strict'
            self.enc = self.encode_list[index-2]

    def get_utfstr(self, string):
        try:
            str_enc = string.encode(self.enc, errors=self.err).decode()
            return str_enc
        except UnicodeError:
            self.err = 'replace'
            str_enc = string.encode(self.enc, errors=self.err).decode()
            return str_enc

    def get_utf2sel(self, string):
        str_enc = string.encode('utf-8').decode(self.enc)
        return str_enc
