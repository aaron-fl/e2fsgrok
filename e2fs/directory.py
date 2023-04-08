from .struct import Struct, pretty_num, read
from .inode import INode128

class DirIter():
    def __init__(self, inode, sb):
        self.inode = inode
        self.sb = sb
        self.blkiter = iter(inode)
        self.blkid = None
        self.dir = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.dir:
            off = self.dir.offset + self.dir.rec_len
            if off == (self.blkid+1)*self.sb.block_size:
                self.blkid = None
            else:
                self.dir = DirectoryEntry(self.inode.stream, off, blkid=self.blkid)
        if self.blkid == None:
            self.blkid = next(self.blkiter)
            #bg = self.blkid // self.sb.blocks_per_group
            if self.sb.blkid_free(self.blkid):# not self.sb.blkgrp(bg).data_bitmap()[self.blkid%self.sb.blocks_per_group]:
                Printer().card(f'Error\tBlock #{self.blkid} is free')
            self.dir = DirectoryEntry(self.inode.stream, self.blkid * self.sb.block_size, blkid=self.blkid)
        return self.dir



class DirectoryBlk():
    def __init__(self, sb, blkid):
        self.sb = sb
        self.blkid = blkid
        self.entries = []
        self._errors = []
        self.parent_inode = None
        self.inode = None
        self.siblings = (None, None)
        

    def validate(self, **kwargs):
        offset = self.blkid * self.sb.block_size
        di = 0
        next_blk = (self.blkid+1)*self.sb.block_size
        while offset < next_blk:
            d = DirectoryEntry(self.sb.stream, offset, blkid=self.blkid)
            for err in d.validate(self.sb.block_size, **kwargs):
                self._errors.append(f"<{di}>{err}")
            offset += d.rec_len or 2*self.sb.block_size
            di += 1
            self.entries.append(d)
        if offset != next_blk:
            self._errors.append(f"rec_len doesn't end on the next block {pretty_num(offset)} != {pretty_num(next_blk)}")
        if self.sb.blkid_free(self.blkid):
            self._errors.append(f"Block {self.blkid} is free")


    def each_entry(self):
        return EntryIter(self)


class EntryIter():
    def __init__(self, dblk):
        self.dblk = dblk
        self.sb = dblk.sb
        self.offset = dblk.blkid * self.sb.block_size
        self.next_blk = (dblk.blkid+1)*self.sb.block_size
    
    def __iter__(self):
        return self

    def __next__(self):
        if self.offset >= self.next_blk: raise StopIteration()
        d = DirectoryEntry(self.sb.stream, self.offset, blkid=self.dblk.blkid) 
        self.offset += d.rec_len or 2*self.sb.block_size
        return d



class DirectoryEntry(Struct):
    size = 8
    enums = {
        'file_type': {
            0:'EXT2_FT_UNKNOWN Unknown File Type',
            1:'EXT2_FT_REG_FILE Regular File',
            2:'EXT2_FT_DIR Directory File',
            3:'EXT2_FT_CHRDEV Character Device',
            4:'EXT2_FT_BLKDEV Block Device',
            5:'EXT2_FT_FIFO Buffer File',
            6:'EXT2_FT_SOCK Socket File',
            7:'EXT2_FT_SYMLINK Symbolic Link',
        }
    }

    flags = {}
    dfn = [
        '<I inode 32bit inode number of the file entry. A value of 0 indicate that the entry is not used.',
        '<H rec_len 16bit unsigned displacement to the next directory entry from the start of the current directory entry. This field must have a value at least equal to the length of the current record.',
        '<B name_len how many bytes of character data are contained in the name.',
        '<B file_type This value must match the inode type defined in the related inode entry.',
    ]

    @property
    def name(self):
        return read(self.stream, self.offset + 8, self.name_len)
        
        
    @property
    def name_utf8(self):
        try:
            return self.name.decode('utf8')
        except:
            return self.name


    def __str__(self):
        return f'{self.name_utf8!r} ({self.name_len}) #{self.blkid} -> {self.inode}'


    def validate(self, block_size, all=False, nonameok=False):
        if self.name_len > self.rec_len-8:
            self._errors.append(f"name longer than record")
            if not all: return self._errors
        if self.offset + self.rec_len > (self.blkid+1)*block_size:
            self._errors.append(f'rec_len past end of block {self.offset + self.rec_len} > {(self.blkid+1)*block_size}')
            if not all: return self._errors
        for c in self.name:
            if c < 32:
                self._errors.append(f"Invalid name chars {c}")
                break
        if not nonameok and self.name == b'':
            self._errors.append(f"No name")
        super().validate(all=all)
        return self._errors

