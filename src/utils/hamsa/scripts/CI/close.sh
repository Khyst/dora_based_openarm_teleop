umount /home/codething/imagine/mnt/run/resolvconf/resolv.conf
umount /home/codething/imagine/mnt/dev
umount /home/codething/imagine/mnt/proc
umount /home/codething/imagine/mnt/root/install.sh
umount /home/codething/imagine/mnt
losetup -d /dev/loop0 /dev/loop1 /dev/loop2/ /dev/loop3
sync
