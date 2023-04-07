import yaclipy as CLI
from math import ceil
from print_ext import Printer, PrettyException
from e2fs import Superblock, Bitmap
from e2fs.struct import pretty_num


def superblocks(*, _input, sb=1024, limit__l=1):
    sb = Superblock(_input, sb)
    i = 0
    for bg, osb in sb.all():
        Printer().hr(f"{bg} : {pretty_num(osb.offset)}")
        if bg == sb.block_group_nr:
            sb.summary(Printer())
            Printer().pretty(sb)
        else:
            sbb.diff(Printer(), sb)
        i += 1
        if i == limit__l: break



def descriptors(*, _input, sb=1024, blkgrp__b=0, verbose__v=False, limit__l=0):
    sb = Superblock(_input, sb)
    for _, blk in sb.all_block_descriptors().items():
        if limit__l and blk.bg >= limit__l: continue
        print(f"#{blk.bg},{blk.bg_src} ({blk.copies}) {blk.block_bitmap_lo}/{blk.inode_bitmap_lo}/{blk.inode_table_lo}  {blk.free_blocks_count_lo}/{blk.free_inodes_count_lo}")



def bitmap(*, _input, sb=1024, blkgrp__b=0):
    sb = Superblock(_input, sb)
    data, inode = sb.bitmaps(blkgrp__b)
    print(f"{sb.blocks_per_group-len(data)} / {sb.blocks_per_group-len(inode)}")


def check_desc(*, _input, sb=1024, blkgrp__b=0):
    sb = Superblock(_input, sb)
    desc = list(sb.block_descriptors(blkgrp__b))
    for d in desc:
        data, inode = sb.bitmaps(d.bg)
        err = False
        if (ldata:=(sb.blocks_per_group-len(data))) != d.free_blocks_count_lo: err = True
        if (linode:=(sb.blocks_per_group-len(inode))) != d.free_inodes_count_lo: err = True
        off = sb.bitmap_offset(d.bg) + d.bg*sb.blocks_per_group
        if off != d.block_bitmap_lo: err = True
        if err: print(err, d.bg, d.block_bitmap_lo,off, '--', d.free_blocks_count_lo,ldata,'--', d.free_inodes_count_lo, linode)
    


@CLI.sub_cmds(superblocks, descriptors, bitmap, check_desc)
def main(fname):
    with open(fname, 'rb') as f:
        yield f
