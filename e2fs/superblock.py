from math import ceil, log
from print_ext import PrettyException, Printer
from datetime import datetime
from .struct import Struct, pretty_num, read
from .block_group import BlockGroup

class Superblock(Struct):
    size = 1024
    flags = {
        'state': {0x0001:'CLEAN Cleanly umounted', 0x0002:'ERRORS Errors detected', 0x0004:'ORPHANS Orphans being recovered'},
        'flags': {
            0x0001:'SIGNED_DIREECTORY Signed directory hash in use.',
            0x0002:'UNSIGNED_DIREECTORY Unsigned directory hash in use.',
            0x0004:'DEV_CODE To test development code.',
        },
        'feature_compat': {
            0x1:'COMPAT_DIR_PREALLOC Directory preallocation.',
            0x2:'COMPAT_IMAGIC_INODES "imagic inodes". Used by AFS to indicate inodes that are not linked into the directory namespace. Inodes marked with this flag will not be added to lost+found by e2fsck.',
            0x4:'COMPAT_HAS_JOURNAL Has a journal.',
            0x8:'COMPAT_EXT_ATTR Supports extended attributes.',
            0x10:'COMPAT_RESIZE_INODE Has reserved GDT blocks for filesystem expansion. Requires RO_COMPAT_SPARSE_SUPER.',
            0x20:'COMPAT_DIR_INDEX Has indexed directories.',
            0x40:'COMPAT_LAZY_BG "Lazy BG". Not in Linux kernel, seems to have been for uninitialized block groups?',
            0x80:'COMPAT_EXCLUDE_INODE "Exclude inode". Intended for filesystem snapshot feature, but not used.',
            0x100:'COMPAT_EXCLUDE_BITMAP "Exclude bitmap". Seems to be used to indicate the presence of snapshot-related exclude bitmaps? Not defined in kernel or used in e2fsprogs.',
            0x200:'COMPAT_SPARSE_SUPER2 Sparse Super Block, v2. If this flag is set, the SB field backup_bgs points to the two block groups that contain backup superblocks.',
        },
        'feature_incompat':{
            0x1:'INCOMPAT_COMPRESSION Compression. Not implemented.',
            0x2:'INCOMPAT_FILETYPE Directory entries record the file type. See ext4_dir_entry_2 below.',
            0x4:'INCOMPAT_RECOVER Filesystem needs journal recovery.',
            0x8:'INCOMPAT_JOURNAL_DEV Filesystem has a separate journal device.',
            0x10:'INCOMPAT_META_BG Meta block groups. See the earlier discussion of this feature.',
            0x40:'INCOMPAT_EXTENTS Files in this filesystem use extents.',
            0x80:'INCOMPAT_64BIT Enable a filesystem size over 2^32 blocks.',
            0x100:'INCOMPAT_MMP Multiple mount protection. Prevent multiple hosts from mounting the filesystem concurrently by updating a reserved block periodically while mounted and checking this at mount time to determine if the filesystem is in use on another host.',
            0x200:'INCOMPAT_FLEX_BG Flexible block groups. See the earlier discussion of this feature.',
            0x400:'INCOMPAT_EA_INODE Inodes can be used to store large extended attribute values.',
            0x1000:'INCOMPAT_DIRDATA Data in directory entry. Allow additional data fields to be stored in each dirent, after struct ext4_dirent. The presence of extra data is indicated by flags in the high bits of ext4_dirent file type flags (above EXT4_FT_MAX). The flag EXT4_DIRENT_LUFID = 0x10 is used to store a 128-bit File Identifier for Lustre. The flag EXT4_DIRENT_IO64 = 0x20 is used to store the high word of 64-bit inode numbers. Feature still in development.',
            0x2000:'INCOMPAT_CSUM_SEED Metadata checksum seed is stored in the superblock. This feature enables the administrator to change the UUID of a metadata_csum filesystem while the filesystem is mounted; without it, the checksum definition requires all metadata blocks to be rewritten.',
            0x4000:'INCOMPAT_LARGEDIR Large directory >2GB or 3-level htree. Prior to this feature, directories could not be larger than 4GiB and could not have an htree more than 2 levels deep. If this feature is enabled, directories can be larger than 4GiB and have a maximum htree depth of 3.',
            0x8000:'INCOMPAT_INLINE_DATA Data in inode. Small files or directories are stored directly in the inode i_blocks and/or xattr space.',
            0x10000:'INCOMPAT_ENCRYPT Encrypted inodes are present on the filesystem.',
        },
        'feature_ro_compat': {
            0x1:'RO_COMPAT_SPARSE_SUPER Sparse superblocks. See the earlier discussion of this feature.',
            0x2:'RO_COMPAT_LARGE_FILE Allow storing files larger than 2GiB.',
            0x4:'RO_COMPAT_BTREE_DIR Was intended for use with htree directories, but was not needed. Not used in kernel or e2fsprogs.',
            0x8:'RO_COMPAT_HUGE_FILE This filesystem has files whose space usage is stored in i_blocks in units of filesystem blocks, not 512-byte sectors. Inodes using this feature will be marked with EXT4_INODE_HUGE_FILE.',
            0x10:'RO_COMPAT_GDT_CSUM Group descriptors have checksums. In addition to detecting corruption, this is useful for lazy formatting with uninitialized groups.',
            0x20:'RO_COMPAT_DIR_NLINK Indicates that the old ext3 32,000 subdirectory limit no longer applies. A directory\'s i_links_count will be set to 1 if it is incremented past 64,999.',
            0x40:'RO_COMPAT_EXTRA_ISIZE Indicates that large inodes exist on this filesystem, storing extra fields after EXT2_GOOD_OLD_INODE_SIZE.',
            0x80:'RO_COMPAT_HAS_SNAPSHOTThis filesystem has a snapshot. Not implemented in ext4.',
            0x100:'RO_COMPAT_QUOTA Quota is handled transactionally with the journal.',
            0x200:'RO_COMPAT_BIGALLOC This filesystem supports "bigalloc", which means that filesystem block allocation bitmaps are tracked in units of clusters (of blocks) instead of blocks.',
            0x400:'RO_COMPAT_METADATA_CSUM This filesystem supports metadata checksumming. (implies RO_COMPAT_GDT_CSUM, though GDT_CSUM must not be set)',
            0x800:'RO_COMPAT_REPLICA Filesystem supports replicas. This feature is neither in the kernel nor e2fsprogs.',
            0x1000:'RO_COMPAT_READONLY Read-only filesystem image; the kernel will not mount this image read-write and most tools will refuse to write to the image.',
            0x2000:'RO_COMPAT_PROJECT: Filesystem tracks project quotas.',
        },
        'default_mount_opts':{
            0x0001:'EXT4_DEFM_DEBUG Print debugging info upon (re)mount.',
            0x0002:'EXT4_DEFM_BSDGROUPS New files take the gid of the containing directory (instead of the fsgid of the current process).',
            0x0004:'EXT4_DEFM_XATTR_USER Support userspace-provided extended attributes.',
            0x0008:'EXT4_DEFM_ACL Support POSIX access control lists (ACLs).',
            0x0010:'EXT4_DEFM_UID16 Do not support 32-bit UIDs.',
            0x0020:'EXT4_DEFM_JMODE_DATA All data and metadata are commited to the journal.',
            0x0040:'EXT4_DEFM_JMODE_ORDERED All data are flushed to the disk before metadata are committed to the journal.',
            0x0060:'EXT4_DEFM_JMODE_WBACK Data ordering is not preserved; data may be written after the metadata has been written.',
            0x0100:'EXT4_DEFM_NOBARRIER Disable write flushes.',
            0x0200:'EXT4_DEFM_BLOCK_VALIDITY Track which blocks in a filesystem are metadata and therefore should not be used as data blocks. This option will be enabled by default on 3.18, hopefully.',
            0x0400:'EXT4_DEFM_DISCARD Enable DISCARD support, where the storage device is told about blocks becoming unused.',
            0x0800:'EXT4_DEFM_NODELALLOC Disable delayed allocation.',
        },
    }

    enums = {
        'errors': {1:'CONTINUE Continue', 2:'REMOUNT_RO Remount read-only', 3:'PANIC Panic'},
        'creator_os': {0:'LINUX Linux', 1:'HURD Hurd', 2:'MASIX Masix', 3:'FREEBSD FreeBSD', 4:'LITES Lites'},
        'rev_level': {0:'V0 Original format',1:'V2 format w/ dynamic inode sizes'},
        'def_hash_version': {
            0:'LEGACY Legacy.',
            1:'HALF_MD4 Half MD4.',
            2:'TEA Tea.',
            3:'LEGACY_UNSIGNED Legacy, unsigned.',
            4:'HALF_MD4_UNSIGNED Half MD4, unsigned.',
            5:'TEA_UNSIGNED Tea, unsigned.',
        },
        'encrypt_algos': {
            0:'ENCRYPTION_MODE_INVALID Invalid algorithm.',
            1:'ENCRYPTION_MODE_AES_256_XTS 256-bit AES in XTS mode.',
            2:'ENCRYPTION_MODE_AES_256_GCM 256-bit AES in GCM mode.',
            3:'ENCRYPTION_MODE_AES_256_CBC 256-bit AES in CBC mode.',
        },
    }


    dfn = [
        '<I inodes_count Total inode count.',
        '<I blocks_count_lo Total block count.',
        '<I r_blocks_count_lo This number of blocks can only be allocated by the super-user.',
        '<I free_blocks_count_lo Free block count.',
        '<I free_inodes_count Free inode count.',
        '<I first_data_block First data block. This must be at least 1 for 1k-block filesystems and is typically 0 for all other block sizes.',
        '<I log_block_size Block size is 2 ^ (10 + log_block_size).',
        '<I log_cluster_size Cluster size is (2 ^ log_cluster_size) blocks if bigalloc is enabled. Otherwise log_cluster_size must equal log_block_size.',
        '<I blocks_per_group Blocks per group.',
        '<I clusters_per_group Clusters per group, if bigalloc is enabled. Otherwise clusters_per_group must equal blocks_per_group.',
        '<I inodes_per_group Inodes per group.',
        '<I mtime Mount time, in seconds since the epoch.',
        '<I wtime Write time, in seconds since the epoch.',
        '<H mnt_count Number of mounts since the last fsck.',
        '<H max_mnt_count Number of mounts beyond which a fsck is needed.',
        '<H magic Magic signature, 0xEF53',
        '<H state File system state. ',
        '<H errors Behaviour when detecting errors.',
        '<H minor_rev_level Minor revision level.',
        '<I lastcheck Time of last check, in seconds since the epoch.',
        '<I checkinterval Maximum time between checks, in seconds.',
        '<I creator_os OS.',
        '<I rev_level Revision level.',
        '<H def_resuid Default uid for reserved blocks.',
        '<H def_resgid Default gid for reserved blocks.',
        '<I first_ino First non-reserved inode.',
        '<H inode_size Size of inode structure, in bytes.',
        '<H block_group_nr Block group # of this superblock.',
        '<I feature_compat Compatible feature set flags. Kernel can still read/write this fs even if it doesn\'t understand a flag; e2fsck will not attempt to fix a filesystem with any unknown COMPAT flags.',
        '<I feature_incompat Incompatible feature set. If the kernel or e2fsck doesn\'t understand one of these bits, it will refuse to mount or attempt to repair the filesystem.',
        '<I feature_ro_compat Readonly-compatible feature set. If the kernel doesn\'t understand one of these bits, it can still mount read-only, but e2fsck will refuse to modify the filesystem.',
        '16s uuid 128-bit UUID for volume.',
        '16s volume_name Volume label.',
        '64s last_mounted Directory where filesystem was last mounted.',
        '<I algorithm_usage_bitmap For compression (Not used in e2fsprogs/Linux)',
        'B prealloc_blocks # of blocks to try to preallocate for ... files? (Not used in e2fsprogs/Linux)',
        'B prealloc_dir_blocks # of blocks to preallocate for directories. (Not used in e2fsprogs/Linux)',
        '<H reserved_gdt_blocks Number of reserved GDT entries for future filesystem expansion.',
        '16s journal_uuid UUID of journal superblock',
        '<I journal_inum inode number of journal file.',
        '<I journal_dev Device number of journal file, if the external journal feature flag is set.',
        '<I last_orphan Start of list of orphaned inodes to delete.',
        '<4I hash_seed HTREE hash seed.',
        'B def_hash_version Default hash algorithm to use for directory hashes.',
        'B jnl_backup_type If this value is 0 or EXT3_JNL_BACKUP_BLOCKS (1), then the jnl_blocks field contains a duplicate copy of the inode\'s i_block[] array and i_size.',
        '<H desc_size Size of group descriptors, in bytes, if the 64bit incompat feature flag is set.',
        '<I default_mount_opts Default mount options.',
        '<I first_meta_bg First metablock block group, if the meta_bg feature is enabled.',
        '<I mkfs_time When the filesystem was created, in seconds since the epoch.',
        '<17I jnl_blocks Backup copy of the journal inode\'s i_block[] array in the first 15 elements and i_size_high and i_size in the 16th and 17th elements, respectively.',
        '<I blocks_count_hi High 32-bits of the block count.',
        '<I r_blocks_count_hi High 32-bits of the reserved block count.',
        '<I free_blocks_count_hi High 32-bits of the free block count.',
        '<H min_extra_isize All inodes have at least # bytes.',
        '<H want_extra_isize New inodes should reserve # bytes.',
        '<I flags Miscellaneous flags.',
        '<H raid_stride RAID stride. This is the number of logical blocks read from or written to the disk before moving to the next disk. This affects the placement of filesystem metadata, which will hopefully make RAID storage faster.',
        '<H mmp_interval # seconds to wait in multi-mount prevention (MMP) checking. In theory, MMP is a mechanism to record in the superblock which host and device have mounted the filesystem, in order to prevent multiple mounts. This feature does not seem to be implemented...',
        '<Q mmp_block Block # for multi-mount protection data.',
        '<I raid_stripe_width RAID stripe width. This is the number of logical blocks read from or written to the disk before coming back to the current disk. This is used by the block allocator to try to reduce the number of read-modify-write operations in a RAID5/6.',
        'B log_groups_per_flex Size of a flexible block group is 2 ^ log_groups_per_flex.',
        'B checksum_type Metadata checksum algorithm type. The only valid value is 1 (crc32c).',
        '<H reserved_pad reserved_pad', 
        '<Q kbytes_written Number of KiB written to this filesystem over its lifetime.',
        '<I snapshot_inum inode number of active snapshot. (Not used in e2fsprogs/Linux.)',
        '<I snapshot_id Sequential ID of active snapshot. (Not used in e2fsprogs/Linux.)',
        '<Q snapshot_r_blocks_count Number of blocks reserved for active snapshot\'s future use. (Not used in e2fsprogs/Linux.)',
        '<I snapshot_list inode number of the head of the on-disk snapshot list. (Not used in e2fsprogs/Linux.)',
        '<I error_count Number of errors seen.',
        '<I first_error_time First time an error happened, in seconds since the epoch.',
        '<I first_error_ino inode involved in first error.',
        '<Q first_error_block Number of block involved of first error.',
        '32s first_error_func Name of function where the error happened.',
        '<I first_error_line Line number where error happened.',
        '<I last_error_time Time of most recent error, in seconds since the epoch.',
        '<I last_error_ino inode involved in most recent error.',
        '<I last_error_line Line number where most recent error happened.',
        '<Q last_error_block Number of block involved in most recent error.',
        '32s last_error_func Name of function where the most recent error happened.',
        '64s mount_opts ASCIIZ string of mount options.',
        '<I usr_quota_inum Inode number of user quota file.',
        '<I grp_quota_inum Inode number of group quota file.',
        '<I overhead_blocks Overhead blocks/clusters in fs. (Huh? This field is always zero, which means that the kernel calculates it dynamically.)',
        '<I backup_bgs0 Block groups containing superblock backups (if sparse_super2)',
        '<I backup_bgs1 Block groups containing superblock backups (if sparse_super2)',
        '4B encrypt_algos Encryption algorithms in use. There can be up to four algorithms in use at any time.',
        '16s encrypt_pw_salt Salt for the string2key algorithm for encryption.',
        '<I lpf_ino Inode number of lost+found',
        '<I prj_quota_inum Inode that tracks project quotas.',
        '<I checksum_seed Checksum seed used for metadata_csum calculations. This value is crc32c(~0, $orig_fs_uuid).',
        '392s end_of_block Padding to the end of the block.',
        '<I checksum Superblock checksum.',
    ]

    def __init__(self, *args, **kwargs):
        self.__inode_count = -1
        super().__init__(*args, **kwargs)


    def validate(self, all=False):
        if self.magic != 0xEF53:
            self._errors.append(f"Bad magic")
            if not all: return self._errors
        if self.blocks_per_group != 8*self.block_size:
            self._errors.append(f'block group size mismatch: {self.blocks_per_group} != {8*self.block_size}')
            if not all: return self._errors
        super().validate(all=all)
        return self._errors


    def _timestamp(self, k):
        return datetime.fromtimestamp(self[k])


    def pretty_lastcheck(self, k):
        return self._timestamp(k)


    def pretty_mkfs_time(self, k):
        return self._timestamp(k)


    def pretty_wtime(self, k):
        return self._timestamp(k)


    def pretty_mtime(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def pretty_first_error_time(self, k):
        return self._timestamp(k) if self[k] else 'Never'


    def pretty_last_error_time(self, k):
        return self._timestamp(k) if self[k] else 'Never'
        

    def super_bgs(self, brute=False):
        if not self.feature_ro_compat & self.RO_COMPAT_SPARSE_SUPER: brute = True
        for bg in range(0, self.bg_count):
            bgrp = self.blkgrp(bg)
            if not (brute or bgrp.is_super()): continue
            sb = Superblock(self.stream, bg*self.bg_size + (0 if bg else 1024))
            sb.validate()
            if sb._errors and sb._errors[0] == "Bad magic": continue
            sb.validate(all=True)
            yield bgrp, sb


    def summary(self, print):
        print(f"{self.name!r} {self.block_size//1024}k/{pretty_num(self.blocks_count_lo*self.block_size)}  {self.bg_count}grps")
        print(self.pretty_val('flags'), ' ', self.pretty_val('feature_compat'), ' ', self.pretty_val('feature_incompat'),' ', self.pretty_val('feature_ro_compat'))


    @property
    def bg_count(self):
        return ceil(self.blocks_count_lo/self.blocks_per_group)


    @property
    def name(self):
        name = self.volume_name
        return name[:name.index(0)].decode('ascii')


    @property
    def block_size(self):
        try:
            return self.__block_size
        except:
            self.__block_size = 2**(10+self.log_block_size)
        return self.__block_size


    @property
    def bg_size(self):
        return self.blocks_per_group*self.block_size


    @property
    def cluster_size(self):
        return 2**(10+self.log_cluster_size)


    @property
    def frag_size(self):
        return 2**(10+self.log_cluster_size)


    def all_block_descriptors(self):
        ''' Collect every descriptor from every super-block-group and organize them by same hash '''
        all_bg = {}
        for bgrp, _ in self.super_bgs():
            for bg_desc in bgrp.descriptors():
                bg_desc.copies = 1
                h = hash(bg_desc.raw())
                if h in all_bg: all_bg[h].copies += 1
                else: all_bg[h] = bg_desc
        return all_bg.values()


    @property
    def inode_count(self):
        if self.__inode_count < 0:
            self.__inode_count = self.inodes_per_group * self.bg_count
        return self.__inode_count


    def valid_blkid(self, blkid, zero_ok=False):
        if blkid < 0: return False
        if blkid >= self.blocks_count_lo: return False
        if blkid == 0: return zero_ok
        bgrp = self.blkgrp(blkid//self.blocks_per_group)
        if blkid < bgrp.inode_table_blkid() + bgrp.inode_block_count: return False
        return True


    def inode(self, id, **kwargs):
        if id < 1 or id >= self.inode_count: raise ValueError(f"inode out of range (1, {self.inode_count})  {id}")
        return self.blkgrp((id - 1) // self.inodes_per_group, **kwargs).inode_idx(id)
        

    def blkgrp(self, bg, **kwargs):
        if bg < 0 or bg >= self.bg_count: raise ValueError(f"bg out of range (0, {self.bg_count})  {bg}")
        return BlockGroup(self, bg, **kwargs)


    def each_blkgrp(self, **kwargs):
        for bg in range(self.bg_count):
            yield self.blkgrp(bg, **kwargs)


    def blkid_free(self, blkid):
        return self.blkgrp(blkid // self.blocks_per_group).blkidx_free(blkid % self.blocks_per_group)


    def inode_free(self, id, **kwargs):
        return not self.blkgrp((id - 1) // self.inodes_per_group, **kwargs).inode_bitmap()[(id-1)%self.inodes_per_group]
