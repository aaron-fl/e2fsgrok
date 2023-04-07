import yaclipy as CLI
from print_ext import Printer
from e2fs import Superblock

def superblocks(*, _input, offset__o=1024):
    sb = Superblock(_input, offset__o)
    sb.validate(all=True)
    sb.summary(Printer())
    Printer().pretty(sb)
    for blk_grp, sbb in sb.backups():
        Printer().hr(f"{blk_grp} : {sbb.offset/1024}")
        sbb.diff(Printer(), sb)


@CLI.sub_cmds(superblocks)
def main(fname):
    with open(fname, 'rb') as f:
        yield f
