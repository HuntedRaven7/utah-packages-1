#!/usr/bin/bash
set -eux

DISK=/var/tmp/parted-disk.img

# Make a temporary disk image to use for tests
fallocate -l 100MiB $DISK

# Make a disklabel and a couple of partitions
parted -s $DISK mklabel gpt
parted -s $DISK mkpart vfat 1MiB 10MiB
parted -s $DISK mkpart ext4 10MiB 50MiB
parted -s $DISK mkpart ext4 50MiB 75MiB
parted -s $DISK set 1 boot
parted -s $DISK set 3 linux-home

# Check p1 for ESP UUID c12a7328-f81f-11d2-ba4b-00a0c93ec93b
P1_TYPE=$(parted -s $DISK --json u MiB p | jq -r '.disk.partitions[0]."type-uuid"')
[ "$P1_TYPE" == "c12a7328-f81f-11d2-ba4b-00a0c93ec93b" ] || exit 1

# Check p2 for linux data type 0fc63daf-8483-4772-8e79-3d69d8477de4
P2_TYPE=$(parted -s $DISK --json u MiB p | jq -r '.disk.partitions[1]."type-uuid"')
[ "$P2_TYPE" == "0fc63daf-8483-4772-8e79-3d69d8477de4" ] || exit 1

# Check p3 for linux home type 933ac7e1-2eb4-4f13-b844-0e14e2aef915
P3_TYPE=$(parted -s $DISK --json u MiB p | jq -r '.disk.partitions[2]."type-uuid"')
[ "$P3_TYPE" == "933ac7e1-2eb4-4f13-b844-0e14e2aef915" ] || exit 1

echo "PASS"
exit 0
