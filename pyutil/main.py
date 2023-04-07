import yaclipy as CLI
from print_ext import Printer
from e2fs import Superblock

def superblocks(*, _input, offset__o=1024):
    sb = Superblock(_input, offset__o)
    sb.validate(all=True)
    Printer().pretty(sb)
    Printer(sb.blocks_count_lo * sb.block_size_in_bytes // 1024)


@CLI.sub_cmds(superblock)
def main(fname):
    with open(fname, 'rb') as f:
        yield f
