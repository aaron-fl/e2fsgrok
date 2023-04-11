import yaclipy as CLI
import pickle, struct, re, hashlib, sys, os
from math import ceil
from print_ext import Printer, PrettyException, Line, Bdr, Text
from e2fs import Superblock, Bitmap
from e2fs.struct import pretty_num, read, Struct
from e2fs.directory import DirectoryBlk
from yaclipy_tools.commands import grep, grep_groups
from yaclipy.arg_spec import coerce_int

def cur_path(*set):
    if set:
        with open('local/curpath.pickle', 'wb') as f:
            pickle.dump(set, f)
    try:
        with open('local/curpath.pickle', 'rb') as f:
            return pickle.load(f)
    except:
        return tuple()



def cur_inode():
    return cur_path()[0]



def name_or_inode(name, inode=None, *, _sb=None):
    try:
        return coerce_int(name)
    except:
        pass
    if not isinstance(inode, Struct): inode = _sb.inode(inode or cur_inode())
    for blkid in inode:
        d = DirectoryBlk(inode.sb, blkid)
        d.validate(all=True)
        if d._errors: raise PrettyException(msg=Text(f"blk #{blkid} Errors\t{full_path}\n",*[f"* {e}\n" for e in d._errors]))
        for e in d.entries:
            if e.name_utf8.lower() == name.lower(): return e.inode
    return 0



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
    Output is #A,B (C) D+E+F  G/H
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
    for d in _sb.all_block_descriptors():
        if limit__l and d.bg >= limit__l: continue
        bgrp = _sb.blkgrp(d.bg)
        line = Line('\b2 $' if bgrp.is_super() else '#', f'{d.bg},{d.bg_src}  (', f'\b2 {d.copies}',')  ')
        n = _sb.blocks_per_group - len(bgrp.data_bitmap())
        line(f"{n} \berr {d.free_blocks_count_lo}" if n != d.free_blocks_count_lo else n, '\bdem /')
        n = _sb.inodes_per_group - len(bgrp.inode_bitmap())
        line(f"{n} \berr {d.free_inodes_count_lo}" if n != d.free_inodes_count_lo else n,'  ')
        off = bgrp.bitmap_offset + d.bg * _sb.blocks_per_group
        line(f"{hex(off)} \berr {hex(d.block_bitmap_lo)}" if off != d.block_bitmap_lo else hex(off),'\bdem +')
        line(f"{1} \berr {d.inode_bitmap_lo-off}" if off+1 != d.inode_bitmap_lo else 1,'\bdem +')
        line(f"{2} \berr {d.inode_table_lo-off}" if off+2 != d.inode_table_lo else 2,'  ')
        Printer(line)



def blkgrp(bg=0, *, _sb, free__f=False):
    ''' Show info about a block group
    
    Parameters:
        <block-group-id>
            The block group number (not block number)
        --free, -f
            Show free blocks
    '''
    bgrp = _sb.blkgrp(bg)
    if free__f:
        bmp = bgrp.data_bitmap()
        Printer('  '.join([str(blkid + bgrp.bg*_sb.blocks_per_group) for blkid in set(range(bmp.size*8)) - set(bmp)]))
    return bgrp



def inode_(inode, *, _sb):
    ''' Show details of an Inode
    '''
    inode = _sb.inode(name_or_inode(inode))
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
                ascii += chr(b) if b > 32 and b < 127 else ' '
                i += 1
                if i%2 == 0: break
            l(' \bdem$' if word == '0'*len(word) else ' ', word)
            if i%32 == 0: break
        Printer(l, '  ', '\bdem |', ascii, '\bdem |')
    


def ls(root_inode=0, *, _sb, depth__d=0, keep_going__k=False, parent__p:int=None):
    ''' Show a directory listing from an inode

    Parameters:
        <inode>
            The inode directory to traverse
        --depth <int>, -d <int> | default=0
            How many layers deep to show
        --keep_going, -k
            Continue even if errors are encountered, otherwise stop on the first error
        --parent <inode>, -p <inode>
            The known parent of the root_inode (for checking purposes)
    '''
    class CollectedErrors(PrettyException):
        def __pretty__(self, print, **kwargs):
            for args,kwargs in self.errors:
                kwargs.setdefault('style','err')
                print.card(*args, **kwargs)
            print(f"{len(self.errors)} Errors", style='err' if self.errors else 'g')

    errs = CollectedErrors(errors=[])
    def _error(*args, **kwargs):
        errs.errors.append((args, kwargs))
        if not keep_going__k: raise errs
        

    def branch(parent_id, inode, depth=0, full_path=''):
        for blkid in inode:
            d = DirectoryBlk(_sb, blkid)
            d.validate(all=True)
            Printer(f'#{blkid}', style='dem')
            if d._errors: _error(f"blk #{blkid} Errors\t{full_path}\n",*[f"* {e}\n" for e in d._errors])
            for e in d.entries:
                path = full_path + f'\bdem /\b {e.name_utf8}\bdem  {hex(e.inode)} \b '
                if e.name == b'' and e.inode == 0: continue
                if e.name == b'.':
                    if e.inode != inode.id: _error(f". Error\t{path}\n* self inode mismatch {hex(e.inode)} != {hex(inode.id)}")
                    continue
                if e.name == b'..':
                    if parent_id != None and e.inode != parent_id:
                        _error(f".. Error\t{path}\n* parent inode mismatch {hex(e.inode)} != {hex(parent_id)}")
                    continue
                try:
                    if e.name in b'..': raise ValueError()
                    child = _sb.inode(e.inode)
                except ValueError:
                    child = None
                if child == None:
                    Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}',)
                    continue
                child.validate(_sb, all=True)
                tail = f'\berr {len(child._errors)} Errors' if child._errors else child.pretty_val('mode')
                Printer('  '*depth, f'\b! {e.name_utf8}', f'  \b1 {hex(e.inode)}', '  ', tail)
                if child._errors: _error(f"inode {hex(child.id)} Errors\t{path}\n", *[f"* {e}\n" for e in child._errors])
                if child.ftype != child.S_IFDIR: continue
                if depth+1 == depth__d: continue
                branch(inode.id, child, depth+1, path)
        return inode
    inode = _sb.inode(root_inode or cur_inode())
    inode.validate(_sb, all=True)
    if inode._errors: _error(f"inode {hex(inode.id)} Errors\t", *[f"* {e}\n" for e in inode._errors])
    branch(parent__p, inode)
    return errs
    


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
                e = iter(dblk)
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
        for e in d:
            name = e.name_utf8
            if name in ['.', '..']: continue
            roots.setdefault(name, {})
            roots[name].setdefault(e.inode, [])
            roots[name][e.inode].append(blkid)
    for name in roots:
        print(f'{name}')
        for inode, blks in roots[name].items():
            print(f'       {inode}  {blks}')
    


def blkls(blkid:int, *, _sb):
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



def search(pattern, *, _sb, fdblks='local/pruned.pickle', fmatches=None, verbose__v=False):
    ''' Search all the identified directory-blocks for a file that matches `pattern`

    Parameters:
        <pattern>
            A regex pattern to match filenames against
    '''
    hval = hashlib.md5(pattern.encode('utf8')).hexdigest()
    if fmatches == None: fmatches = f"local/search/{hval}.pickle"
    pat = re.compile(pattern)
    with open(fdblks, 'rb') as f:
        dblks = pickle.load(f)
        blkids = set()
        for blks in dblks.values(): blkids.update(blks)
    try:
        with open(fmatches, 'rb') as f:
            matches = pickle.load(f)
    except:
        matches = set()
        with Printer().progress(f"searching for {pattern!r} -> {fmatches}", height_max=10) as p:
            for bi, blkid in enumerate(blkids):
                if bi%4096 == 0:
                    p(f"{bi}/{len(blkids)} {bi*100/len(blkids):.1f}%  found: {len(matches)} ", tag={'progress':(bi,len(blkids))})
                d = DirectoryBlk(_sb, blkid)
                for e in d:
                    try: assert(pat.fullmatch(e.name_utf8, re.I))
                    except: continue
                    matches.add( blkid )
                    break
        with open(fmatches, 'wb') as f:
            pickle.dump(matches, f)
    for blkid in matches:
        if verbose__v:
            blkls(blkid, _sb=_sb)
            continue
        d = DirectoryBlk(_sb, blkid)
        for e in d:
            try: assert(pat.fullmatch(e.name_utf8, re.I))
            except: continue
            Printer(f"{blkid} : ", Line(style='!').insert(0,e.name_utf8),f" {hex(e.inode)}")
            break
    Printer(f"{len(matches)} blocks found from {fmatches}")



def isearch(inode:int, *, _sb, fdblks='local/pruned.pickle', fmatches=None):
    ''' Find all directory entries that point to this inode
    '''
    if fmatches == None: fmatches = f"local/isearch/{hex(inode)}.pickle"
    with open(fdblks, 'rb') as f:
        dblks = pickle.load(f)
        blkids = set()
        for blks in dblks.values(): blkids.update(blks)
    try:
        with open(fmatches, 'rb') as f:
            matches = pickle.load(f)
    except:
        matches = set()
        with Printer().progress(f"searching for entries pointing to {inode!r}", height_max=10) as print:
            for bi, blkid in enumerate(blkids):
                if bi%4096 == 0:
                    print(f"{bi}/{len(blkids)} {bi*100/len(blkids):.1f}%  found: {len(matches)} ", tag={'progress':(bi,len(blkids))})
                d = DirectoryBlk(_sb, blkid)
                for e in d:
                    if e.inode != inode: continue
                    matches.add(blkid)
                    break
        with open(fmatches, 'wb') as f:
            pickle.dump(matches, f)
    for blkid in matches:
        blkls(blkid, _sb=_sb)
    print(len(matches))



def areyousure():
    Printer(f"\berr Are you sure?")
    d = input('[y/N]')
    if d != 'y': raise PrettyException(msg="Aborting")



def change_block(inode, index:int, blkid:int, *, _sb):
    ''' Change one of the blkids of an inode

    Parameters:
        <inode>
            Which inode's block to modify
        <index>
            which block entry to modify
        <blkid>
            What new blockid to insert
    '''
    inode = inode_(inode, _sb=_sb)
    l = list(inode.block)
    l[index] = blkid
    Printer(f"OLD Blocks: ", inode.block)
    Printer(f"NEW Blocks: ", tuple(l))
    areyousure()
    offset = inode.offset + inode.flds['block'][0] + 4*index
    data = struct.pack('<I', blkid)
    _sb.stream.seek(offset)
    _sb.stream.write(data)
    Printer("Wrote:", data, " to ", pretty_num(offset))



def change_blkcount(nblks:int, *, _sb):
    ''' Change one of the blkids of an inode

    Parameters:
        <inode>
            Which inode's block to modify
        <nblks>
            How many blocks should it have
    '''
    inode = inode_(inode, _sb=_sb)
    new_lo = nblks * (2<<_sb.log_block_size)
    Printer(f"Change blocks_lo from {inode.blocks_lo} -> {new_lo}?")
    areyousure()
    offset = inode.offset + inode.flds['blocks_lo'][0]
    data = struct.pack('<I', new_lo)
    _sb.stream.seek(offset)
    _sb.stream.write(data)
    Printer("Wrote:", data, " to ", pretty_num(offset))



def change_dir_entry(blkid:int, name, inode:int, *, _sb):
    ''' Change one of the directory entries' inodes

    Parameters:
        <blkid>
            The dblk of entries to modify
        <name>
            The filename who's inode you want to change
        <inode>
            The new inode that filename should point to
    '''
    blkls(blkid, _sb=_sb)
    d = DirectoryBlk(_sb, blkid)
    for e in d:
        if e.name_utf8 == name: break   
    else:
        Printer(f"{name!r} not found in dblk #{blkid}", style='err')
        return
    Printer(f"Change: \b1 {name}\b 's inode from {hex(e.inode)} => {hex(inode)}")
    areyousure()
    offset = e.offset + e.flds['inode'][0]
    data = struct.pack('<I', inode)
    _sb.stream.seek(offset)
    _sb.stream.write(data)
    Printer("Wrote:", data, " to ", pretty_num(offset))



def cp(inode, dest, *, _sb):
    ''' Copy a file to some external destination
    '''
    inode = _sb.inode(name_or_inode(inode))
    Printer(inode)
    if inode.ftype != inode.S_IFREG: raise PrettyException(msg=f"Bad file type {inode.pretty_val('ftype')}")
    with open(dest, 'wb') as f:
        size = inode.size_lo
        for blkid in inode:
            data = read(_sb.stream, blkid*_sb.block_size, min(size, _sb.block_size))
            print(f"Read {len(data)} from {blkid}")
            size -= len(data)
            f.write(data)



def cat(inode, *, _sb, binary__b=False, encoding='utf8'):
    ''' Show the contents inode's data blocks
    '''
    inode = _sb.inode(name_or_inode(inode, _sb=_sb))
    Printer(repr(inode))
    for data in inode.each_line(32 if binary__b else 4096, not binary__b):
        if not binary__b:
            sys.stdout.buffer.write(data)
            continue
        line = Line()
        ascii = ''
        for i,b in enumerate(data):
            is_ascii = (b >32 and b < 127)
            if i and i%4==0: line(' ')
            if i and i%2==0: line(' ')
            line(f"{b:02x}", style='dem' if b==0 else 'y' if is_ascii else '')
            
            ascii += chr(b) if is_ascii else ' '
        Printer(line, f"\bdem {Bdr.codes['- - ']}", ascii, f"\bdem {Bdr.codes['- - ']}")



def cd(name='', inode=0, *, _sb):
    ''' Show the contents inode's data blocks
    '''
    if inode or not name:
        return cur_path(inode or 2, name)
    inode = name_or_inode(name, _sb=_sb)
    if not inode: raise PrettyException(msg=Text(f'\b1 {name}\b : No such file or directory'))
    return cur_path(inode, name)



@CLI.sub_cmds(grep, change_dir_entry, change_block, superblocks, descriptors, blkgrp, root_inodes, inode_, blk_data, ls, find_blk_dirs, blkls, find_inode_dirs, dotfiles, rootfiles, search, change_blkcount, isearch, cp,cd, cat)
def main(*, sb=1024, write__w=False, fname__f=None):
    grep_groups({
        'e2fs': [('py', 'e2fs', '*/__pycache__/*')],
        'pyutil': [('py', 'pyutil', '*/__pycache__/*')],
    })
    if not fname__f: fname__f = os.environ.get('IMG_FILE', None)
    if fname__f:
        with open(fname__f, 'r+b' if write__w else 'rb') as f:
            yield dict(_sb=Superblock(f, sb))
    else:
        yield None
