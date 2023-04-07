import struct, functools
from print_ext import PrettyException
from .struct import pretty_num


class BitmapIter():
    def __init__(self, bitmap):
        self.bitmap = bitmap
        self.byte = 0
        self.offset = 0
        self.bit = 0
        self.idx = -1


    def __next__(self):
        while self.offset < self.bitmap.size:
            if self.bit == 0:
                self.byte = self.bitmap.byte(self.offset)
            used = self.byte & (1<<self.bit)
            self.idx += 1
            self.bit += 1
            if self.bit == 8:
                self.offset += 1
                self.bit = 0
            if used: return self.idx
        if self.offset == self.bitmap.size: raise StopIteration()



class Bitmap():
    def __init__(self, stream, offset, size, **kwargs):
        self.size = size
        self.offset = offset
        self.stream = stream
        for k,v in kwargs.items(): setattr(self, k, v)


    def byte(self, offset):
        try:
            self.stream.seek(offset+self.offset)
        except OSError:
            raise PrettyException(msg=f'EOF {pretty_num(offset+self.offset)} / {pretty_num(self.stream.seek(0,io.SEEK_END))}')
        data = self.stream.read(1)
        if len(data) != 1:
            raise PrettyException(msg=f"EOF")
        return struct.unpack_from('B', data)[0]


    def __iter__(self):
        return BitmapIter(self)


    def __len__(self):
        sum = 0
        for i in range(self.size):
            byte = self.byte(i)
            sum += functools.reduce(lambda a, i: a + bool(byte&(1<<i)), range(8), 0)
        return sum
