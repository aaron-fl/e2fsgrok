import yaclipy as CLI
import pickle
from math import ceil
from print_ext import Printer, PrettyException, Line
from e2fs import Superblock, Bitmap
from e2fs.struct import pretty_num
from e2fs.directory import DirectoryBlk
from yaclipy_tools.commands import grep, grep_groups

# FIXME
# Lost+found
# etc
# var

# Root INODE  2051 -> 2107

# Inode 0x21
#    2051 ( 0x1a8002)

# Inode 0x1a8001


# Possible var
#  18799877
#  !! 57979448 0x1a8001
#  1744896


def superblocks(*, _input, sb=1024, limit__l=1):
    sb = Superblock(_input, sb)
    i = 0
    for bgrp, osb in sb.super_bgs():
        Printer().hr(f"{bgrp.bg} : {pretty_num(osb.offset)}")
        if bgrp.bg == sb.block_group_nr:
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



def bgrp(*, _input, sb=1024, blkgrp__b=0):
    sb = Superblock(_input, sb)
    return sb.blkgrp(blkgrp__b)


def check_desc(*, _input, sb=1024, blkgrp__b=0):
    sb = Superblock(_input, sb)
    bgrp = sb.blkgrp(blkgrp__b)
    for d in bgrp.descriptors():
        data = bgrp.data_bitmap()
        inode = bgrp.inode_bitmap()
        err = False
        if (ldata:=(sb.blocks_per_group-len(data))) != d.free_blocks_count_lo: err = True
        if (linode:=(sb.inodes_per_group-len(inode))) != d.free_inodes_count_lo: err = True
        off = bgrp.bitmap_offset() + d.bg*sb.blocks_per_group
        if off != d.block_bitmap_lo: err = True
        if err: print(err, d.bg, d.block_bitmap_lo, off, '--', d.free_blocks_count_lo, ldata,'--', d.free_inodes_count_lo, linode)
    

def inode_(inode=2, *, _input, sb=1024):
    ''' Show details of an Inode '''
    sb = Superblock(_input, sb)
    inode = sb.inode(inode)
    inode.validate(sb, all=True)
    Printer().hr(f"{hex(inode.id)} #{inode.bg} {'free' if inode.is_free else ''}  nblks: {inode.block_count}")
    return inode



def root_inodes(*, _input, sb=1024):
    sb = Superblock(_input, sb)
    for i, msg in enumerate(['Defective blocks', 'Root directory', 'User quota','Group quota','Boot loader','Undelete directory','resize','journal', 'exclude', 'replica', 'lost_found']):
        Printer().hr(f"{i+1} {msg}")
        inode = sb.inode(i+1)
        Printer().pretty(inode)



def inode_data(inode=2, *, _input, sb=1024):
    sb = Superblock(_input, sb)
    inode = inode_(inode, _input=_input, sb=sb.offset)
    for blkid in inode:
        errs, data = sb.blk_data(blkid)
        Printer().hr(blkid,'  ', pretty_num(blkid*sb.block_size))
        if errs: Printer().card('Errors\t', *[f'* {e}\n' for e in errs])
        offset = 0
        while offset < sb.block_size:
            Printer(Line(data[offset:offset+256]))
            offset += 256




def ls(root_inode=2, *, _input, sb=1024, depth__d=0, continue__c=False):
    nerrors = 0
    def _error(*args, **kwargs):
        nonlocal nerrors
        kwargs.setdefault('style','err')
        Printer().card(*args, **kwargs)
        nerrors+=1
        if not continue__c: raise PrettyException(msg='error encountered')
        
    def branch(sb, parent_id, inode, depth=0):
        inode.validate(sb, all=True)
        if inode._errors: _error(f"inode {hex(inode.id)} Errors\t", *[f"* {e}\n" for e in inode._errors])
        for blkid in inode:
            d = DirectoryBlk(sb, blkid)
            d.validate(all=True, nonameok=True)
            Printer(f'#{blkid}', style='dem')
            if d._errors: _error(f"blk #{blkid} Errors\t", *[f"* {e}\n" for e in d._errors])
            for e in d.entries:
                if e.name == b'' and e.inode == 0: continue
                if e.name == b'.':
                    if e.inode != inode.id: _error(f". Error\t* self inode mismatch {hex(e.inode)} != {hex(inode.id)}")
                    continue
                if e.name == b'..':
                    if parent_id !='unk' and e.inode != parent_id:
                        _error(f".. Error\t* parent inode mismatch {hex(e.inode)} != {hex(parent_id)}")
                    continue
                try:
                    if e.name in b'..': raise ValueError()
                    child = sb.inode(e.inode)
                except ValueError:
                    Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}',)
                    continue
                Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}', '  ', child.pretty_val('mode'))
                if child.ftype != child.S_IFDIR: continue
                if depth+1 == depth__d: continue
                branch(sb, inode.id, child, depth+1)
        return inode

    sb = Superblock(_input, sb)
    branch(sb, 'unk', sb.inode(root_inode))
    Printer(f"{nerrors} Errors", style='err' if nerrors else 'g')
    



def scan_dir(*, _input, sb=1024, fname='local/scan_dir.pickle'):
    ''' Search every block for blocks that look like directory entries '''
    sb = Superblock(_input, sb)
    def save(data):
        with open(fname, 'wb') as f:
            pickle.dump(data, f)
    try:
        with open(fname, 'rb') as f:
            bg, blkids = pickle.load(f)
    except:
        bg, blkids = 0, set()
    with Printer().progress(f"from {bg}", height_max=10) as print:
        while bg < sb.bg_count:
            print(f'#{bg}/{sb.bg_count} {len(blkids)}', tag={'progress':(bg, sb.bg_count)})
            for blkid in sb.blkgrp(bg).each_data_blkid():
                dirs = sb.dirs(blkid)
                if not dirs: continue
                blkids.add(blkid)
                print(f'#{bg}.{blkid}  {len(blkids)}', tag={'progress':(bg, sb.bg_count)})
            save((bg, blkids))
            bg += 1
    Printer(f"Done: {len(blkids)}")



def scan_inodes(*, _input, sb=1024, fname='local/scan_inodes.pickle'):
    ''' Scan every inode for inodes that are directories '''
    sb = Superblock(_input, sb)
    def save(data):
        with open(fname, 'wb') as f:
            pickle.dump(data, f)
    try:
        with open(fname, 'rb') as f:
            idstart, ids = pickle.load(f)
    except:
        idstart, ids = 1, {}
    total = sb.inodes_per_group*sb.bg_count
    with Printer().progress(f"from {idstart}", height_max=10) as print:
        for id in range(idstart, total):
            if id%(1024*2) == 0:
                print(f"{id} / {total} {id*100/total:.1f}%   {len(ids)} {len(ids[tuple()])}", tag={'progress':(id, total)})
                save((id, ids))
            inode = sb.inode(id)
            if inode.ftype != 0x4000: continue
            inode.validate(sb)
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
    #print(ids)



def prune_dir(*, _input, sb=1024, show__s=None, fixup=False, fin='local/scan_dir.pickle', fname='local/pruned.pickle'):
    sb = Superblock(_input, sb)

    with open(fin, 'rb') as f:
        blkid, blkids = pickle.load(f)
    try:
        with open(fname, 'rb') as f:
            errs = pickle.load(f)
    except:
        errs = {}
        with Printer().progress('go', height_max=10) as print:
            for i, blkid in enumerate(blkids):
                if i%(1024) == 0:
                    print(f'#{i}/{len(blkids)}', tag={'progress':(i, len(blkids))})
                dblk = DirectoryBlk(sb, blkid)
                dblk.validate()
                errstr = '--'.join(sorted(dblk._errors))
                errs.setdefault(errstr, set())
                errs[errstr].add(blkid)
        with open(fname, 'wb') as f:
            pickle.dump(errs, f)

    if fixup:
        ers2 = {'': errs['']}
        for estr, vals in errs.items():
            if not estr: continue
            eset = set()
            for err in estr.split('--'):
                if 'Invalid value' in err: eset.add('val')
                elif 'longer' in err: eset.add('long')
                elif 'rec_len' in err: eset.add('rlen')
                elif 'name chars' in err: eset.add('chars')
                elif 'No name' in err: eset.add('noname')
                elif 'is free' in err: eset.add('free')
            eset = tuple(sorted(eset))
            ers2.setdefault(eset, set())
            ers2[eset].update(vals)

        with open(fname, 'wb') as f:
            pickle.dump(ers2, f)


    if show__s == None:
        for errstr, blkids in errs.items():
            Printer(len(blkids), ' : ', errstr)
        Printer(len(errs), ' kinds')
    else:
        for blkid in errs[show__s]:
            dblk = DirectoryBlk(sb, blkid)
            dblk.validate()
            names = ' '.join(f'{e.name_utf8!r}{hex(e.inode)}' for e in dblk.entries)
            Printer(blkid, ' : ', names)


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
    



def dblk(blkid:int, *, _input, sb=1024):
    ''' Show the contents of a directory block '''
    sb = Superblock(_input, sb)
    Printer().hr(blkid)
    d = DirectoryBlk(sb, blkid)
    d.validate(all=True, nonameok=True)
    if d._errors: Printer().card(f"Errors\t", *[f"* {e}\n" for e in d._errors], style='err')
    for e in d.entries:
        try:
            inode = sb.inode(e.inode)
        except:
            inode = None
        if inode:
            inode.validate(sb)
            istr = f'\berr {len(inode._errors)} Errors' if inode._errors else f"{inode.pretty_val('mode')}"
            if inode.is_free: istr +=' free'
        else:
            istr = '\berr Invalid inode ID'
        Printer(f"\b! {e.name_utf8} \b \b1 {hex(e.inode)}\b  {istr}")




def www(*,_input, sb=1024, fdblks='local/pruned.pickle', fpc='local/www.pickle'):
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




@CLI.sub_cmds(grep, superblocks, descriptors, bgrp, check_desc, root_inodes, inode_, ls, scan_dir, dblk, prune_dir, scan_inodes, dotfiles, rootfiles, www)
def main(*, fname__f=None):
    grep_groups({
        'e2fs': [('py', 'e2fs', '*/__pycache__/*')],
        'pyutil': [('py', 'pyutil', '*/__pycache__/*')],
    })

    if fname__f:
        with open(fname__f, 'rb') as f:
            yield f
    else:
        yield None
