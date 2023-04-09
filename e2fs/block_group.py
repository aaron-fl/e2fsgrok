from math import ceil, log
from print_ext import PrettyException
from .bitmap import Bitmap
from .inode import INode128
from .block_descriptor import BlockDescriptor32, BlockDescriptor64


class BlockGroup():
    def __init__(self, sb, bg, calc=True):
        self.sb = sb
        self.bg = bg
        self.calc = calc


    
    def is_super(self):
        if self.calc:
            is_pow = lambda n, base: int(x:=log(n, base)) == x
            return self.bg==0 or is_pow(self.bg,3) or is_pow(self.bg,5) or is_pow(self.bg, 7)
        # Guess
        raise NotImplementedError()
        sb = Superblock(self.stream, bg * self.bg_size + (0 if bg else 1024))
        return None if sb.validate() else sb
    

    @property
    def bitmap_offset(self):
        if self.is_super():
            return 1 + self.bg_desc_blocks_count + self.sb.reserved_gdt_blocks
        return 0


    def inode_bitmap(self):
        return Bitmap(self.sb.stream, self.bg*self.sb.bg_size + (self.bitmap_offset + 1)*self.sb.block_size, self.sb.inodes_per_group//8)


    def data_bitmap(self):
        return Bitmap(self.sb.stream, self.bg*self.sb.bg_size + (self.bitmap_offset + 0)*self.sb.block_size, self.sb.block_size)


    def inode_table_blkid(self):
        assert(self.bg >= 0)
        return self.bg*self.sb.blocks_per_group + self.bitmap_offset + 2


    @property
    def bg_desc_blocks_count(self):
        return ceil(self.sb.bg_count * self.BlockDescriptor.size / self.sb.block_size)


    @property
    def inode_block_count(self):
        return ceil(self.sb.inode_size * self.sb.inodes_per_group / self.sb.block_size)


    def each_data_blkid(self):
        blkid = self.inode_table_blkid() + self.inode_block_count
        while blkid < self.sb.blocks_count_lo and blkid < (self.bg+1)*self.sb.blocks_per_group:
            yield blkid
            blkid += 1


    def blkidx_free(self, index):
        return not self.data_bitmap()[index]


    def inode_idx(self, id):
        index = (id - 1) % self.sb.inodes_per_group
        assert(self.sb.inode_size == 128), f'Only 128 byte inodes are supported, not {self.sb.inode_size}'
        return INode128(self.sb.stream, index * self.sb.inode_size + self.inode_table_blkid()*self.sb.block_size, bg=self.bg, id=id, sb=self.sb, is_free = not self.inode_bitmap()[index])

    @property
    def BlockDescriptor(self):
        return BlockDescriptor64 if self.sb.desc_size > 32 else BlockDescriptor32
    

    def descriptors(self):
        if not self.is_super():
            raise PrettyException(msg=f"no superblock at bg#{self.bg}")
        for i in range(self.sb.bg_count):
            yield self.BlockDescriptor(self.sb.stream, self.bg * self.sb.bg_size + self.sb.block_size + i*self.BlockDescriptor.size, bg=i, bg_src=self.bg)
        

    def __pretty__(self, print, **kwargs):
        data = self.data_bitmap()
        inode = self.inode_bitmap()
        print(f"BlockGroup #{self.bg}", '  SUPER' if self.is_super() else '', f'free data/inode: {self.sb.blocks_per_group-len(data)} / {self.sb.inodes_per_group-len(inode)}')
