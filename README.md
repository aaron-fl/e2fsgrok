# e2fsgrok - investigate ext2 ext3 ext4 filesystems

https://ext4.wiki.kernel.org/index.php/Ext4_Disk_Layout#The_Super_Block
https://www.nongnu.org/ext2-doc/ext2.html#bg-block-bitmap


## TLDR;

The original /dev/sdd2 LVM-v0 filesystem got corrupted.
That partition was copied to the raid `/mnt/md1/sdd2_lvm.img`.
From there the broken ext3 filesystem was extracted from the lvm volume and copied to `/mnt/md1/sdd2.img.orig`.
That image was tweaked to gain access to the kvm images.
`e2fsck` was then run to make it mountable.

This fixed image can be mounted to gain access to the kvm images

```
 $ mount /mnt/md1/sdd2.img.orig /mnt/broken_sdd2 -o loop
 $ cd "/mnt/broken_sdd2/var/#64454657/gconf/gconf.xml.defaults/%gconf-tree-zh_HK.xml/libvirt/images"
```

The images are:
 * `Huskie.img` : Primary web server files
 * `Pug.img` : beer
 * `Bulldog.img` : unkown
 * `Aibo.img` : swap space
 * `Beagle.img` : swap space

The Pug.img contains two partitions.  The second partition can accessed via a loopback device.

```
 $ losetup --offset $((512*1026048)) --sizelimit $((512*80893952)) --show --find Pug.img
 /dev/loopXX
```

Next, the logical volume on `/dev/loopXX` can be activated, and the `centos/root` volume mounted.

```
 $ vgdisplay
 $ vgchange -ay centos
 $ mount /dev/centos/root /mnt/centos
```

Look for mongo info.

```
 $ cat /mnt/centos/etc/mongod.conf
 $ ls /mnt/centos/var/lib/mongo
```

## List of interesting objects

* #2051 in 0x2 : '.'0x21 '..'0x2  Lost and found stuff
* #2052 in 0xb : NOT a d-block.  Looks like indirect block data.
* #2053 in 0xb : '.'0x2  '..'0x2   An old root folder?  It contains lost+found pointing to 0x21
* #2054 in 0xb : '.'0xc '..'0x21   man srvadmin-rac4 doc java srvadmin-omilcore applications pixmaps
* #2055 in 0xb : '.'0xd '..'0x21   man3 man8 man4
* #2107 : '.'0x2 '..'0x2   The 'real' root
* 0x21 : appears to be an old lost+found directory (from #2053).  It contains #2051 which is incorrectly in the root 0x2.
* 0x1a8001 : the var directory, but it is zeroed
* 0x3d78201 : A better var directory '..'0x3d781c3 '../..'0x3d781b2 '../../..'0x3d78001 '../../../..'0x2


## Fixes

The root inode (0x2) is pointing to d-block 2051.  But that d-block is lost+found stuff.

* change inode 0x2 blocks index 0 from 2051 to 2107  $ change_block 2 0 2107

The lost+found inode (0xb) has 4 confused d-blocks (2052 2053 2054 2055).
I wanted to use 2051, but it has too many things to fix.
So lets just use 2055

* $ change_block 0xb 0 2055
* $ change_block 0xb 1 0
* $ change_block 0xb 2 0
* $ change_block 0xb 3 0
* 0xd->0xb  $ change_dir_entry 2055 "." 0xb
* 0x21->0x2  $ change_dir_entry 2055 ".." 0x2

the three man directories in 2055 need to be reparented from 0xd to 0xb: 27911083, 27911263, 27912346

* $ change_dir_entry 27911083 ".." 0xb
* Repeat for 27911263 27912346

boot, sys, proc, dev, etc, tmp, root, selinux, lib64, usr, bin, home, lib, media, mnt, opt, sbin, srv, misc, net
 folders' parent is pointing to 0x21.  Move it to root

* $ change_dir_entry 50831360 ".." 0x2
* Repeat for 9183232 52535296 23601152 64462848 59351040 31760384 26746880 33005568 4530176 17113088 62431232 73728 19472384 27893760 33857536 43196416 22618112 15165440

The var directory points to zeroed inode 0x1a8001.  
It probably should have been  0x1a8001/ #57979448 but all it's entries point to 0x0.
I found a better one at 0x3d78201/#1744896.

* $ change_dir_entry 2107 "var" 0x3d78201
* $ change_dir_entry 1744896 ".." 0x2

var/lib,tmp,cache,log,db,empty,games  points to zeored inodes 0x1a8002,0x1a8004,0x1a8005,0x1a801b,0x1a801c,0x1a801d,0x1a801e
Lets hard-link those to 'opt'0x1a8026, because, why not?

* $ change_dir_entry 1744896 "lib" 0x1a8026
* Repeat for tmp cache log db empty games

/etc 0x3d78001 /gconf 0x3d781b2 /gconf.xml.defaults 0x3d781b6 /%gconf-tree-zh_HK.xml 0x3d78202 has broken directories:
  rpm 0x1a8003 1 Errors
  games 0x1a801f 1 Errors
  misc 0x1a8020 1 Errors

Lets hard-link those to 'alternatives'0x1a802d, because, why not?

* change_dir_entry 1744897 "rpm" 0x1a802d
* Repeat for games misc


/etc 0x3d78001 /gconf is full of errors
Let's just hard-link it to  0x3d781ae 

* change_dir_entry 64465165 "gconf" 0x3d781ae


/etc 0x3d78001 /dmesg 0x1a8008  is invalid.  hard- link it to 0x1a8236

* change_dir_entry 1745127 "dmesg" 0x1a8236


/opt 0x1a98001 /dell 0x1a98002 /srvadmin 0x1a98003 /lib64 0x1a98004 /openmanage 0x1a9803b /apache-tomcat 0x1aa002a  has 16 errors.  hard-link it to 0x1ab0ac3

* change_dir_entry 27910800 "apache-tomcat" 0x1ab0ac3

/var 0x3d78201 /lock 0x1a8022 /subsys 0x1a8023 /kudzu 0x1a800e  is invalid.   Hard-link it to 0x1a8037

* change_dir_entry 1745150 "kudzu" 0x1a8037

/var 0x3d78201 /run 0x1a8028 /utmp 0x1a8007 is invalid.  Hard-link it to 0x1b011c

* change_dir_entry 1745154 "utmp" 0x1a80e5
* change_dir_entry 1745154 ".." 0x3d78201

/usr 0x1f78001 /share 0x1f78003 /doc 0x1f78004 /gtk2-devel-2.10.4 0x20407a0 /examples 0x20407a1 has a bad 'label' directory.  Hard-link it to 'list'0x20407d5

* change_dir_entry 33829993 "label" 0x20407d5

/opt 0x1a98001 /dell 0x1a98002 /srvadmin 0x1a98003 /lib64 0x1a98004 /openmanage 0x1a9803b /jre 0x1a98a15 /man 0x1a98d2a /ja_JP.UTF-8 0x1aa0001 is Invalid.  Hard Link it to 'ja'0x3340016

* change_dir_entry 27950241 "ja_JP.UTF-8" 0x3340016


# Descriptors
   525,1  (12)  34 0/32762  0x1068000+1+2

   243,1  (12)  32430 0/30700 32768  0x798000 0x798401+1 1026+2 1027
   243,0  (1 )  32430 0/30700 32768  0x798000 0x798401+1 1026+2 1027
   125,1  (12)  32430 0/30700 32768  0x3e8000 0x3e8401+1 1026+2 1027
   125,0  (1 )  32430 0/30700 32768  0x3e8000 0x3e8401+1 1026+2 1027
   53,1   (12)  4555 0/32008 32011  0x1a8000+1+2
   54,1   (12)  983 0/32380  0x1b0000+1+2

Possible var
        0x1a8001  57979448  Abandoned lost and found
  0x3d78201 1744896


# VirtualBox


There seem to be some different images :
    /root/ダウンロード
    /var/lib/libvirt/images/Huskie.img
    /root/ダウンロード/CentOS-7.0-1406-x86_64-NetInstall.iso
    /var/lib/libvirt/images/Pug.img

These have been deleted:
    <MachineEntry uuid="{e2893f6a-b30c-49be-b175-6727ad870197}" src="/root/VirtualBox VMs/Teria/Teria.vbox"/>
    <MachineEntry uuid="{7c78daf9-1e16-4d7f-9cbc-52d09fee4232}" src="/root/VirtualBox VMs/Dacs/Dacs.vbox"/>


Other important places
/var/lib/libvirt/qemu

libvirt 0x3d78736  (contains storage directory)
libvirt  0x1b0129  (contains log files)
libvirt 0x1b0123 **JACKPOT!!!!**
  Huskie.img  0x1b0166  frw-------,---  848M
  Bulldog.img  0x1a28001  frwxr-xr-x,---  848M
  Beagle.img  0x1b0119  frw-------,---  1G784M
  Aibo.img  0x1b0143  frw-------,---  3G544M
  Pug.img  0x1b0132  frw-------,---  3G64M


usr/lib/virtualbox/postinst-common.sh

local/images/Huskie.img1 *        63    208844    208782  102M 83 Linux
local/images/Huskie.img2      208845 102398309 102189465 48.7G 8e Linux LVM

# Bulldog

This is where the DB is

15028248 0x1a28001 0xe5000a 0x1b0126 Bulldog.img
0x21/#64454657/gconf/gconf.xml.defaults/%gconf-tree-zh_HK.xml/libvirt/images

local/images/Bulldog.img1 *        63    208844    208782  102M 83 Linux
local/images/Bulldog.img2      208845 102398309 102189465 48.7G 8e Linux LVM


# Pug

1777988 0x1b0132 0x1b0126 0x1b0123 Pug.img

local/images/Pug.img1 *       2048  1026047  1024000  500M 83 Linux
local/images/Pug.img2      1026048 81919999 80893952 38.6G 8e Linux LVM


# Aibo

Just swap space

local/images/Aibo.img1 *       2048  1026047  1024000  500M 83 Linux
local/images/Aibo.img2      1026048 40959999 39933952   19G 8e Linux LVM


# Beagle

Just swap space

local/images/Beagle.img1 *       2048  1026047  1024000  500M 83 Linux
local/images/Beagle.img2      1026048 20479999 19453952  9.3G 8e Linux LVM
