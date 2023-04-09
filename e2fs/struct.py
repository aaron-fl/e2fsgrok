import io, struct, functools
from print_ext import Table, PrettyException


def read(stream, offset, size):
    try:
        stream.seek(offset)
    except OSError:
        raise PrettyException(msg=f'EOF {pretty_num(offset)} / {pretty_num(stream.seek(0,io.SEEK_END))}')
    data = stream.read(size)
    if len(data) != size:
        raise PrettyException(msg=f"need {size}bytes, got {len(data)}")
    return data


def pretty_num(n):
    s = []
    factor = 1024*1024*1024*1024*1024
    for unit in 'PTGMk':
        if f := n // factor:
            s.append(f'{f}\bdem {unit}\b ')
            n -= f*factor
        factor //= 1024
    if not s or n: s.append(str(n))
    return ''.join(s)



class MetaStruct(type):
    def __new__(self, name, bases, dict):
        dict['doc'] = {}
        dict['flds'] = {}
        enums = dict.pop('enums')
        flags = dict.pop('flags').copy()
        dict['_enums'] = {}
        dict['_flags'] = {}
        assert(not enums.keys()&flags.keys()), f"{enums.keys()}  {flags.keys()}"
        flags.update(enums)
        for name, vals in flags.items():
            d = dict['_enums' if name in enums else '_flags']
            d[name] = {}
            for val, txt in vals.items():
                ename, edoc = txt.split(' ',1)
                assert(ename not in dict), ename
                assert(ename not in dict['doc']), ename
                dict[ename] = val
                dict['doc'][ename] = edoc
                d[name][val] = ename
        offset = 0
        for line in dict.get('dfn', []):
            format, name, doc = line.split(' ', 2)
            assert(name not in dict), name
            assert(name not in dict['doc']), name
            dict['doc'][name] = doc
            dict['flds'][name] = (offset, struct.calcsize(format), format)
            offset += dict['flds'][name][1]
        if offset != dict.get('size', 0):
            raise ValueError(f"Struct size {offset} != {dict['size']}")
        return super().__new__(self, name, bases, dict)


class Struct(metaclass=MetaStruct):
    enums = {}
    flags = {}

    def __init__(self, stream, offset=0, **kwargs):
        self.stream = stream
        self.offset = offset
        self._errors = []
        self.__cache = {}
        for k,v in kwargs.items(): setattr(self, k, v)


    def validate(self, all=False):
        for fld, vals in self._enums.items():
            val = self[fld]
            for v in val if isinstance(val, tuple) else [val]:
                if v not in vals:
                    self._errors.append(f"Invalid value {val!r} for {fld!r}")
                    if not all: return self._errors
        for fld, vals in self._flags.items():
            all = functools.reduce(lambda a,b: a|b, vals.keys())
            val = self[fld]
            for v in val if isinstance(val, tuple) else [val]:
                if v&~all:
                    self._errors.append(f"Invalid value {val!r} for {fld!r}")
                    if not all: return self._errors
        return self._errors


    def raw(self):
        return read(self.stream, self.offset, self.size)


    def __getitem__(self, key):
        if key in dir(self): return getattr(self, key)
        try:
            return self.__cache[key]
        except KeyError:
            pass
        if key not in self.flds:
            raise AttributeError(f"{key} is not a field")
        offset, size, format = self.flds[key]
        data = read(self.stream, offset + self.offset, size)
        self.__cache[key] = struct.unpack_from(format, data)
        if len(self.__cache[key]) == 1: self.__cache[key] = self.__cache[key][0]
        return self.__cache[key]


    def __getattr__(self, key):
        return self[key]


    def pretty_val(self, k):
        try:
            return getattr(self, f'pretty_{k}')(k)
        except AttributeError:
            pass
        val = self[k]
        if k in self._enums:
            return tuple([self._enums[k].get(v,'?') for v in val]) if isinstance(val, tuple) else self._enums[k].get(val,'?')
        if k in self._flags:
            return ' '.join([name for flg, name in self._flags[k].items() if flg&val])
        return val


    def __pretty__(self, print, **kwargs):
        tbl = Table(1,1,tmpl='pad')
        tbl.cell('C0', style='1', just='>')
        for fld in self.flds:
            val = str(self[fld])
            pval = str(self.pretty_val(fld))
            if pval == val: val = ''
            tbl(fld, '\t', pval,'\t')#, self.doc[fld].replace('\t', ' ')[:40],'\t')
        print(tbl)
        if self._errors:
            print.card('Errors\t', *[f'* {e}\n' for e in self._errors], style='err')


    def diff(self, print, other):
        tbl = Table(1,1,1)
        for fld in self.flds:
            if self[fld] == other[fld]: continue
            val = str(self[fld])
            pval = str(self.pretty_val(fld))
            if pval == val: val = ''
            tbl(fld, '\t', val[:40], '\t', pval[:100],'\t')#, self.doc[fld].replace('\t', ' ')[:40],'\t')
        print(tbl)
        if self._errors:
            print.card('Errors\t', *[f'* {e}\n' for e in self._errors], style='err')
