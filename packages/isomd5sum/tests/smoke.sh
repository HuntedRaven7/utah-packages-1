#!/bin/sh -eux

# Create testing iso image
rm -rf ./isocontent
mkdir isocontent
dd if=/dev/zero of=isocontent/big_enough_file  bs=500K  count=1
mkisofs -o test.iso isocontent

# Implant and check md5 sum
implantisomd5 test.iso
checkisomd5 --verbose test.iso 2>&1 | tee test.run.log

echo "Check implanted checksum for 1.2.4-1 checksum bug"
grep ';FR' test.run.log && exit 1

# Destroy testing iso image
rm -rf ./isocontent
rm test.iso
rm test.run.log
