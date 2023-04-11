from datetime import datetime
import struct
from .struct import Struct, read, pretty_num

enums = {
    'ftype': {
        0x1000:'p FIFO',
        0x2000:'c Character device',
        0x4000:'d Directory',
        0x6000:'b Block device',
        0x8000:'f Regular file',
        0xA000:'l Symbolic link',
        0xC000:'s Socket',
    },
}

flags = {
    'mode': {
        0x1:'S_IXOTH (Others may execute)',
        0x2:'S_IWOTH (Others may write)',
        0x4:'S_IROTH (Others may read)',
        0x8:'S_IXGRP (Group members may execute)',
        0x10:'S_IWGRP (Group members may write)',
        0x20:'S_IRGRP (Group members may read)',
        0x40:'S_IXUSR (Owner may execute)',
        0x80:'S_IWUSR (Owner may write)',
        0x100:'S_IRUSR (Owner may read)',
        0x200:'S_ISVTX (Sticky bit)',
        0x400:'S_ISGID (Set GID)',
        0x800:'S_ISUID (Set UID)',
        0x1000:'S_IFIFO FIFO',
        0x2000:'S_IFCHR Character device',
        0x4000:'S_IFDIR Directory',
        0x6000:'S_IFBLK Block device',
        0x8000:'S_IFREG Regular file',
        0xA000:'S_IFLNK Symbolic link',
        0xC000:'S_IFSOCK Socket',
    },
    'flags': {
        0x1:'EXT4_SECRM_FL This file requires secure deletion. (not implemented)',
        0x2:'EXT4_UNRM_FL This file should be preserved, should undeletion be desired. (not implemented)',
        0x4:'EXT4_COMPR_FL File is compressed. (not really implemented)',
        0x8:'EXT4_SYNC_FL All writes to the file must be synchronous.',
        0x10:'EXT4_IMMUTABLE_FL File is immutable.',
        0x20:'EXT4_APPEND_FL File can only be appended.',
        0x40:'EXT4_NODUMP_FL The dump(1) utility should not dump this file.',
        0x80:'EXT4_NOATIME_FL Do not update access time.',
        0x100:'EXT4_DIRTY_FL Dirty compressed file. (not used)',
        0x200:'EXT4_COMPRBLK_FL File has one or more compressed clusters. (not used)',
        0x400:'EXT4_NOCOMPR_FL Do not compress file. (not used)',
        0x800:'EXT4_ENCRYPT_FL Encrypted inode. This bit value previously was EXT4_ECOMPR_FL (compression error), which was never used.',
        0x1000:'EXT4_INDEX_FL Directory has hashed indexes.',
        0x2000:'EXT4_IMAGIC_FL AFS magic directory.',
        0x4000:'EXT4_JOURNAL_DATA_FL File data must always be written through the journal.',
        0x8000:'EXT4_NOTAIL_FL File tail should not be merged. (not used by ext4)',
        0x10000:'EXT4_DIRSYNC_FL All directory entry data should be written synchronously (see dirsync).',
        0x20000:'EXT4_TOPDIR_FL Top of directory hierarchy.',
        0x40000:'EXT4_HUGE_FILE_FL This is a huge file.',
        0x80000:'EXT4_EXTENTS_FL Inode uses extents.',
        0x200000:'EXT4_EA_INODE_FL Inode stores a large extended attribute value in its data blocks.',
        0x400000:'EXT4_EOFBLOCKS_FL This file has blocks allocated past EOF. (deprecated)',
        0x01000000:'EXT4_SNAPFILE_FL Inode is a snapshot. (not in mainline)',
        0x04000000:'EXT4_SNAPFILE_DELETED_FL Snapshot is being deleted. (not in mainline)',
        0x08000000:'EXT4_SNAPFILE_SHRUNK_FL Snapshot shrink has completed (not in mainline)',
        0x10000000:'EXT4_INLINE_DATA_FL Inode has inline data.',
        0x20000000:'EXT4_PROJINHERIT_FL Create children with the same project ID.',
        0x80000000:'EXT4_RESERVED_FL Reserved for ext4 library.',
        # Aggregate flags:
        # 0x4BDFFF User-visible flags.
        # 0x4B80FF User-modifiable flags. Note that while EXT4_JOURNAL_DATA_FL and EXT4_EXTENTS_FL can be set with setattr, they are not in the kernel's EXT4_FL_USER_MODIFIABLE mask, since it needs to handle the setting of these flags in a special manner and they are masked out of the set of flags that are saved directly to i_flags.

    },
}
dfn = [
    '<H mode File mode.',
    '<H uid Lower 16-bits of Owner UID.',
    '<I size_lo Lower 32-bits of size in bytes.',
    '<I atime Last access time, in seconds since the epoch. However, if the EA_INODE inode flag is set, this inode stores an extended attribute value and this field contains the checksum of the value.',
    '<I ctime Last inode change time, in seconds since the epoch. However, if the EA_INODE inode flag is set, this inode stores an extended attribute value and this field contains the lower 32 bits of the attribute value\'s reference count.',
    '<I mtime Last data modification time, in seconds since the epoch. However, if the EA_INODE inode flag is set, this inode stores an extended attribute value and this field contains the number of the inode that owns the extended attribute.',
    '<I dtime Deletion Time, in seconds since the epoch.',
    '<H gid Lower 16-bits of GID.',
    '<H links_count Hard link count. Normally, ext4 does not permit an inode to have more than 65,000 hard links. This applies to files as well as directories, which means that there cannot be more than 64,998 subdirectories in a directory (each subdirectory\'s \'..\' entry counts as a hard link, as does the \'.\' entry in the directory itself). With the DIR_NLINK feature enabled, ext4 supports more than 64,998 subdirectories by setting this field to 1 to indicate that the number of hard links is not known.',
    '<I blocks_lo Lower 32-bits of "block" count. If the huge_file feature flag is not set on the filesystem, the file consumes i_blocks_lo 512-byte blocks on disk. If huge_file is set and EXT4_HUGE_FILE_FL is NOT set in inode.i_flags, then the file consumes i_blocks_lo + (i_blocks_hi << 32) 512-byte blocks on disk. If huge_file is set and EXT4_HUGE_FILE_FL IS set in inode.i_flags, then this file consumes (i_blocks_lo + i_blocks_hi << 32) filesystem blocks on disk.',
    '<I flags Inode flags.',
    '<I version Inode version. However, if the EA_INODE inode flag is set, this inode stores an extended attribute value and this field contains the upper 32 bits of the attribute value\'s reference count.',

    '<15I block Block map or extent tree. See the section "The Contents of inode.i_block".',
    '<I generation File version (for NFS).',
    '<I file_acl_lo Lower 32-bits of extended attribute block. ACLs are of course one of many possible extended attributes; I think the name of this field is a result of the first use of extended attributes being for ACLs.',
    '<I size_high Upper 32-bits of file/directory size. In ext2/3 this field was named i_dir_acl, though it was usually set to zero and never used.',
    '<I obso_faddr (Obsolete) fragment address.',
    '<H blocks_high Upper 16-bits of the block count. Please see the note attached to i_blocks_lo.',
    '<H file_acl_high Upper 16-bits of the extended attribute block (historically, the file ACL location). See the Extended Attributes section below.',
    '<H uid_high Upper 16-bits of the Owner UID.',
    '<H gid_high Upper 16-bits of the GID.',
    '<H checksum_lo Lower 16-bits of the inode checksum.',
    '<H reserved0 Unused.'
    '<H extra_isize Size of this inode - 128. Alternately, the size of the extended inode fields beyond the original ext2 inode, including this field.',
]



class BlkIterator():
    def __init__(self, inode):
        self.sb = inode.sb
        self.inode = inode
        self.idx = 0
        self.maxi = inode.block_count
        self.id0_max = 12 + self.sb.block_size // 4

    def __iter__(self):
        return self

    def __next__(self):
        while self.idx < self.maxi:
            idx = self.idx
            self.idx += 1
            if idx < 12:
                blkid = self.inode.block[idx]
            elif idx < self.id0_max:
                offset = self.inode.block[12] * self.sb.block_size + 4*(idx-12)
                blkid = struct.unpack_from('<I', read(self.inode.stream, offset, 4))[0]
            else:
                print(f'!!!! {self.maxi} !!!')
                raise NotImplemented()
            if blkid == 0: continue
            return blkid
        if self.idx == self.maxi: raise StopIteration()



class INode(Struct):
    size = 0
    enums = enums
    flags = flags

    def _timestamp(self, k):
        return datetime.fromtimestamp(self[k])


    @property
    def ftype(self):
        return self.mode & 0xf000


    @property
    def block_count(self):
        return self.blocks_lo//(2<<self.sb.log_block_size)


    def pretty_mode(self, k):
        v = self[k]
        mode = self.mode
        s = self._enums['ftype'].get(self.ftype,'?')
        s += 'r' if mode & self.S_IRUSR else '-'
        s += 'w' if mode & self.S_IWUSR else '-'
        s += 'x' if mode & self.S_IXUSR else '-'
        s += 'r' if mode & self.S_IRGRP else '-'
        s += 'w' if mode & self.S_IWGRP else '-'
        s += 'x' if mode & self.S_IXGRP else '-'
        s += 'r' if mode & self.S_IROTH else '-'
        s += 'w' if mode & self.S_IWOTH else '-'
        s += 'x' if mode & self.S_IXOTH else '-'
        s += ','
        s += 'u' if mode & self.S_ISUID else '-'
        s += 'g' if mode & self.S_ISGID else '-'
        s += 't' if mode & self.S_ISVTX else '-'
        return s
        

    def pretty_atime(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def pretty_ctime(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def pretty_mtime(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def pretty_dtime(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def __iter__(self):
        return BlkIterator(self)


    def each_line(self, line_size, nl=True, size=-1):
        if size < 0: size = self.size_lo
        data = bytearray()
        blkids = iter(self)
        while True:
            idx = -1
            try:
                if not nl: raise ValueError()
                idx = data.index(10)+1
            except ValueError:
                if len(data) > line_size:
                    idx = line_size
            if idx < 0: # Try to read another block
                try:
                    if not (read_size:=min(size, self.sb.block_size)): raise StopIteration()
                    blkid = next(blkids)
                except StopIteration:
                    if data: yield data
                    return
                data.extend(read(self.stream, blkid*self.sb.block_size, read_size))                
            else:
                size -= len(data[:idx])
                yield data[:idx]
                data[:idx] = []




    def validate(self, sb, all=False):
        if sb.inode_free(self.id):
            self._errors.append('free')
        super().validate(all=all)
        return self._errors


    def __repr__(self):
        return f"{hex(self.id)} {self.pretty_val('mode')} {pretty_num(self.size_lo)} bytes"



class INode128(INode):
    size = 128
    enums = enums
    flags = flags
    dfn = dfn

   
    

class INode158(INode):
    size = 158
    enums = enums
    flags = flags
    dfn = dfn + [
        '<H checksum_hi Upper 16-bits of the inode checksum.',
        '<I ctime_extra Extra change time bits. This provides sub-second precision. See Inode Timestamps section.',
        '<I mtime_extra Extra modification time bits. This provides sub-second precision.',
        '<I atime_extra Extra access time bits. This provides sub-second precision.',
        '<I crtime File creation time, in seconds since the epoch.',
        '<I crtime_extra Extra file creation time bits. This provides sub-second precision.',
        '<I version_hi Upper 32-bits for version number.',
        '<I projid Project ID.',
    ]


