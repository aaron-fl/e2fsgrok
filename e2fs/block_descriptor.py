from .struct import Struct

flags = {
    'flags': {
        0x1:'EXT4_BG_INODE_UNINIT inode table and bitmap are not initialized.',
        0x2:'EXT4_BG_BLOCK_UNINIT block bitmap is not initialized.',
        0x4:'EXT4_BG_INODE_ZEROED inode table is zeroed.',
    },
}

dfn = [
    '<I block_bitmap_lo Lower 32-bits of location of block bitmap.',
    '<I inode_bitmap_lo Lower 32-bits of location of inode bitmap.',
    '<I inode_table_lo Lower 32-bits of location of inode table.',
    '<H free_blocks_count_lo Lower 16-bits of free block count.',
    '<H free_inodes_count_lo Lower 16-bits of free inode count.',
    '<H used_dirs_count_lo Lower 16-bits of directory count.',
    '<H flags Block group flags.',
    '<I exclude_bitmap_lo Lower 32-bits of location of snapshot exclusion bitmap.',
    '<H block_bitmap_csum_lo Lower 16-bits of the block bitmap checksum.',
    '<H inode_bitmap_csum_lo Lower 16-bits of the inode bitmap checksum.',
    '<H itable_unused_lo Lower 16-bits of unused inode count. If set, we needn\'t scan past the (sb.inodes_per_group - gdt.itable_unused)th entry in the inode table for this group.',
    '<H checksum Group descriptor checksum; crc16(sb.uuid+group+desc) if the RO_COMPAT_GDT_CSUM feature is set, or crc32c(sb.uuid+group_desc) & 0xFFFF if the RO_COMPAT_METADATA_CSUM feature is set.',
]



class BlockDescriptor32(Struct):
    size = 32
    dfn = dfn
    flags = flags
    enums = {}

    def __str__(self):
        return f"#{self.bd}  {self.block_bitmap_lo}/{self.inode_bitmap_lo}/{self.inode_table_lo}   {self.free_blocks_count_lo}/{self.free_inodes_count_lo}"



class BlockDescriptor64(BlockDescriptor32):
    size = 64
    flags = flags
    enums = {}
    dfn = dfn + [
        '<I block_bitmap_hi Upper 32-bits of location of block bitmap.',
        '<I inode_bitmap_hi Upper 32-bits of location of inodes bitmap.',
        '<I inode_table_hi Upper 32-bits of location of inodes table.',
        '<H free_blocks_count_hi Upper 16-bits of free block count.',
        '<H free_inodes_count_hi Upper 16-bits of free inode count.',
        '<H used_dirs_count_hi Upper 16-bits of directory count.',
        '<H itable_unused_hi Upper 16-bits of unused inode count.',
        '<I exclude_bitmap_hi Upper 32-bits of location of snapshot exclusion bitmap.',
        '<H block_bitmap_csum_hi Upper 16-bits of the block bitmap checksum.',
        '<H inode_bitmap_csum_hi Upper 16-bits of the inode bitmap checksum.',
        'I pad Padding to 64 bytes.',
    ]
