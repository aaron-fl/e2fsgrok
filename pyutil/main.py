import yaclipy as CLI
import pickle
from math import ceil
from print_ext import Printer, PrettyException, Line
from e2fs import Superblock, Bitmap
from e2fs.struct import pretty_num, read
from e2fs.directory import DirectoryBlk
from yaclipy_tools.commands import grep, grep_groups

# FIXME
# Lost+found
# etc
# var

# Root INODE  2051 -> 2107

# Inode 0x21
#    2051 ( 0x1a8002)

# Inode 0x1a8001 #53
#   ALL ZEROS 


# Possible var
#  18799877
#  !! 57979448 0x1a8001
#  1744896


def superblocks(*, _sb, limit__l=1):
    ''' Show superblock info

    Parameters:
        --limit <int>, -l <int>
            Only show this many superblocks (of the backup copies)
    '''
    i = 0
    for bgrp, osb in _sb.super_bgs():
        Printer().hr(f"{bgrp.bg} : {pretty_num(osb.offset)}")
        if bgrp.bg == _sb.block_group_nr:
            _sb.summary(Printer())
            Printer().pretty(_sb)
        else:
            sbb.diff(Printer(), _sb)
        i += 1
        if i == limit__l: break



def descriptors(*, _sb, limit__l=0):
    ''' Show descriptors for a given block.
    Output is #A,B (C) D/E/F  G/H
     * A : block group id
     * B : super-block-group that this descriptor was found in
     * C : Number of identical descriptors in other super-block-groups
     * D : Blk bitmap blkid
     * E : Inode bitmap blkid
     * F : Inode table blkid
     * G : Number of free blocks
     * H : Number of free inodes

    Parameters:
        --limit <int>, -l <int>
            Only show descriptors for the first `-l` descriptors
    '''
    for blk in _sb.all_block_descriptors():
        if limit__l and blk.bg >= limit__l: continue
        print(f"#{blk.bg},{blk.bg_src} ({blk.copies}) {blk.block_bitmap_lo}/{blk.inode_bitmap_lo}/{blk.inode_table_lo}  {blk.free_blocks_count_lo}/{blk.free_inodes_count_lo}")



def blkgrp(bg=0, *, _sb):
    ''' Show info about a block group
    
    Parameters:
        <block-group-id>
            The block group number (not block number)
    '''
    return _sb.blkgrp(bg)



def check_desc(bg=0, *, _sb):
    ''' Analyze the descriptors in a block-group to find discrepancies
    Output: A  B  C
    Parameters:
        <block-group-id>
            The block group number (not block number) who's discrepancy table needs checking
    '''
    bgrp = _sb.blkgrp(bg)
    for d in bgrp.descriptors():
        data = bgrp.data_bitmap()
        inode = bgrp.inode_bitmap()
        err = ''
        if (ldata:=(_sb.blocks_per_group-len(data))) != d.free_blocks_count_lo: err += 'blk_count '
        if (linode:=(_sb.inodes_per_group-len(inode))) != d.free_inodes_count_lo: err += 'inode_count '
        off = bgrp.bitmap_offset() + d.bg * _sb.blocks_per_group
        if off != d.block_bitmap_lo: err += 'offset'
        if err: Printer(err, f'  \b1 {d.bg}',f'  {d.block_bitmap_lo} {off} --  {d.free_blocks_count_lo} {ldata}  --  {d.free_inodes_count_lo} {linode}')



def inode_(id=2, *, _sb):
    ''' Show details of an Inode
    '''
    inode = _sb.inode(id)
    inode.validate(_sb, all=True)
    Printer().hr(f"{hex(inode.id)} #{inode.bg} {'free' if inode.is_free else ''}  nblks: {inode.block_count}")
    return inode



def root_inodes(*, _sb):
    ''' Show the first 11 inodes
    '''
    for id, msg in enumerate(['Defective blocks', 'Root directory', 'User quota','Group quota','Boot loader','Undelete directory','resize','journal', 'exclude', 'replica', 'lost_found']):
        inode = _sb.inode(id+1)
        inode.validate(_sb, all=True)
        Printer().hr(f"{hex(inode.id)} \b2 {msg}\b  nblks: {inode.block_count}")
        Printer().pretty(inode)



def blk_data(blkid=0, *, _sb):
    ''' Show raw data of a block

    Parameters:
        <blkid>
            The block ID to show
    '''
    bgrp = _sb.blkgrp(blkid // _sb.blocks_per_group)
    Printer().hr(f"#{blkid}  bg:{bgrp.bg}", " @ ", pretty_num(blkid*_sb.block_size),  '  free' if bgrp.blkidx_free(blkid % _sb.blocks_per_group) else '  in use')
    data = read(_sb.stream, blkid*_sb.block_size, _sb.block_size)
    i = 0
    while i < _sb.block_size:
        l = Line()
        ascii = ''
        while i < _sb.block_size:
            word = ''
            while i < _sb.block_size:
                b = data[i]
                word += f"{b:02x}"
                ascii += chr(b) if b > 32 and b < 128 else ' '
                i += 1
                if i%2 == 0: break
            l(' \bdem$' if word == '0'*len(word) else ' ', word)
            if i%32 == 0: break
        Printer(l, '  ', '\bdem |', ascii, '\bdem |')
    


def ls(root_inode=2, *, _sb, depth__d=0, keep_going__k=False):
    ''' Show a directory listing from an inode

    Parameters:
        <inode>
            The inode directory to traverse
        --depth <int>, -d <int> | default=0
            How many layers deep to show
        --keep_going, -k
            Continue even if errors are encountered, otherwise stop on the first error 
    '''
    nerrors = 0
    def _error(*args, **kwargs):
        nonlocal nerrors
        kwargs.setdefault('style','err')
        Printer().card(*args, **kwargs)
        nerrors+=1
        if not continue__c: raise PrettyException(msg='error encountered')
        
    def branch(parent_id, inode, depth=0):
        inode.validate(_sb, all=True)
        if inode._errors: _error(f"inode {hex(inode.id)} Errors\t", *[f"* {e}\n" for e in inode._errors])
        for blkid in inode:
            d = DirectoryBlk(_sb, blkid)
            d.validate(all=True, nonameok=True)
            Printer(f'#{blkid}', style='dem')
            if d._errors: _error(f"blk #{blkid} Errors\t", *[f"* {e}\n" for e in d._errors])
            for e in d.entries:
                if e.name == b'' and e.inode == 0: continue
                if e.name == b'.':
                    if e.inode != inode.id: _error(f". Error\t* self inode mismatch {hex(e.inode)} != {hex(inode.id)}")
                    continue
                if e.name == b'..':
                    if parent_id != None and e.inode != parent_id:
                        _error(f".. Error\t* parent inode mismatch {hex(e.inode)} != {hex(parent_id)}")
                    continue
                try:
                    if e.name in b'..': raise ValueError()
                    child = _sb.inode(e.inode)
                except ValueError:
                    Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}',)
                    continue
                Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}', '  ', child.pretty_val('mode'))
                if child.ftype != child.S_IFDIR: continue
                if depth+1 == depth__d: continue
                branch(inode.id, child, depth+1)
        return inode

    branch(None, _sb.inode(root_inode))
    Printer(f"{nerrors} Errors", style='err' if nerrors else 'g')
    


def find_blk_dirs(fname='local/scan_dir.pickle', *, _sb):
    ''' Search every block for blocks that look like directory entries

    Parameters:
        <filename>  | default='local/scan_dir.pickle'
            Where to save the data
    '''
    def save(data):
        with open(fname, 'wb') as f:
            pickle.dump(data, f)
    try:
        with open(fname, 'rb') as f:
            bg, blkids = pickle.load(f)
    except:
        bg, blkids = 0, set()
    with Printer().progress(f"from {bg}", height_max=10) as print:
        while bg < _sb.bg_count:
            print(f'#{bg}/{_sb.bg_count} {len(blkids)}', tag={'progress':(bg, _sb.bg_count)})
            for blkid in _sb.blkgrp(bg).each_data_blkid():
                d = DirectoryBlk(_sb, blkid)
                d.validate(all=True)
                if d._errors: continue # FIXME: more lax
                blkids.add(blkid)
                print(f'#{bg}.{blkid}  {len(blkids)}', tag={'progress':(bg, _sb.bg_count)})
            save((bg, blkids))
            bg += 1
    Printer(f"Done: {len(blkids)}")



def find_inode_dirs(fname='local/scan_inodes.pickle', *, _sb):
    ''' Scan every inode for inodes that are directories
    
    Parameters:
        <filename>  | default='local/scan_inodes.pickle'
            Where to save the data
    '''
    def save(data):
        with open(fname, 'wb') as f:
            pickle.dump(data, f)
    try:
        with open(fname, 'rb') as f:
            idstart, ids = pickle.load(f)
    except:
        idstart, ids = 1, {}
    with Printer().progress(f"from {idstart}", height_max=10) as print:
        for id in range(idstart, _sb.inode_count):
            if id%(1024*2) == 0:
                print(f"{id} / {_sb.inode_count} {id*100/_sb.inode_count:.1f}%   {len(ids)} {len(ids[tuple()])}", tag={'progress':(id, _sb.inode_count)})
                save((id, ids))
            inode = _sb.inode(id)
            if inode.ftype != 0x4000: continue
            inode.validate(_sb)
            eset = set()
            for e in inode._errors:
                if 'free' in e: eset.add('free')
                elif 'Invalid value' in err: eset.add('val')
            eset = tuple(sorted(eset))
            ids.setdefault(eset, set())
            ids[eset].add(inode.id)
    save((id, ids))
    for k,v in ids.items():
        Printer(f"{len(v)} : {k}")
    Printer(f"Done: ", len(ids))



def dotfiles(*,_input, sb=1024, fdblks='local/pruned.pickle', fpc='local/parent_child.pickle'):
    sb = Superblock(_input, sb)
    with open(fdblks, 'rb') as f:
        dblks = pickle.load(f)
    try:
        with open(fpc, 'rb') as f:
            mappings = pickle.load(f)
    except:
        mappings = set()
        bi = 0
        for e, blks in dblks.items():
            for blkid in blks:
                if (bi:=bi+1)%10000 == 0:
                    print(f"{bi} {len(mappings)}")
                dblk = DirectoryBlk(sb, blkid)
                e = iter(dblk.each_entry())
                d0 = next(e)
                if d0.name != b'.': continue
                d1 = next(e)
                assert(d1.name == b'..')
                mappings.add( (blkid, d0.inode, d1.inode) )
        with open(fpc, 'wb') as f:
            pickle.dump(mappings, f)
    for m in mappings:
        print(m)


def rootfiles(*, _input, sb=1024, fpc='local/parent_child.pickle'):
    sb = Superblock(_input, sb)
    with open(fpc, 'rb') as f:
        fpc = pickle.load(f)
    roots = {}
    for blkid, inode, pnode in fpc:
        if inode != 2: continue
        print(f"{blkid} {hex(inode)} {hex(pnode)}")
        d = DirectoryBlk(sb, blkid)
        for e in d.each_entry():
            name = e.name_utf8
            if name in ['.', '..']: continue
            roots.setdefault(name, {})
            roots[name].setdefault(e.inode, [])
            roots[name][e.inode].append(blkid)
    for name in roots:
        print(f'{name}')
        for inode, blks in roots[name].items():
            print(f'       {inode}  {blks}')
    


def dblk(blkid:int, *, _sb):
    ''' Show the contents of a directory block
    '''
    Printer().hr(blkid)
    d = DirectoryBlk(_sb, blkid)
    d.validate(all=True)
    if d._errors: Printer().card(f"Errors\t", *[f"* {e}\n" for e in d._errors], style='err')
    for e in d.entries:
        try:
            inode = _sb.inode(e.inode)
        except:
            inode = None
        if inode:
            inode.validate(_sb)
            istr = f'\berr {len(inode._errors)} Errors' if inode._errors else f"{inode.pretty_val('mode')}"
            if inode.is_free: istr +=' free'
        else:
            istr = '\berr Invalid inode ID'
        Printer(f"\b! {e.name_utf8} \b \b1 {hex(e.inode)}\b  {istr}")



def www(*, _sb, fdblks='local/pruned.pickle', fpc='local/www.pickle'):
    sb = Superblock(_input, sb)
    with open(fdblks, 'rb') as f:
        dblks = pickle.load(f)
    try:
        with open(fpc, 'rb') as f:
            mappings = pickle.load(f)
    except:
        mappings = set()
        bi = 0
        for e, blks in dblks.items():
            for blkid in blks:
                if (bi:=bi+1)%10000 == 0:
                    print(f"{bi} {len(mappings)}")
                d = DirectoryBlk(sb, blkid)
                for e in d.each_entry():
                    if e.name != b'www': continue
                    mappings.add( blkid )
                    break
        with open(fpc, 'wb') as f:
            pickle.dump(mappings, f)
    for blkid in mappings:
        dblk(blkid, _input=sb.stream)
    print(len(mappings))




@CLI.sub_cmds(grep, superblocks, descriptors, blkgrp, check_desc, root_inodes, inode_, blk_data, ls, find_blk_dirs, dblk, find_inode_dirs, dotfiles, rootfiles, www)
def main(*, sb=1024, write__w=False, fname__f=None):
    grep_groups({
        'e2fs': [('py', 'e2fs', '*/__pycache__/*')],
        'pyutil': [('py', 'pyutil', '*/__pycache__/*')],
    })

    if fname__f:
        with open(fname__f, 'asdf' if write__w else 'rb') as f:
            yield dict(_sb=Superblock(f, sb))
    else:
        yield None
