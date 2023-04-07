import yaclipy as CLI
from print_ext import Printer, PrettyException
from e2fs import Superblock
from e2fs.struct import pretty_num


def superblocks(*, _input, offset__o=1024):
    sb = Superblock(_input, offset__o)
    sb.validate(all=True)
    sb.summary(Printer())
    Printer().pretty(sb)
    for blk_grp, sbb in sb.backups():
        Printer().hr(f"{blk_grp} : {sbb.offset/1024}")
        sbb.diff(Printer(), sb)


def descriptors(*, _input, blkgrp__b=0, verbose__v=0, limit__l=0):
    sb = Superblock(_input, 1024)
    i = 0
    for bd in sb.block_descriptors(blkgrp__b):
        if verbose__v:
            Printer().hr(str(bd))
            Printer().pretty(bd)
        else:
            Printer(str(bd))
        i += 1
        if i == limit__l: break



@CLI.sub_cmds(superblocks, descriptors)
def main(fname):
    with open(fname, 'rb') as f:
        yield f
