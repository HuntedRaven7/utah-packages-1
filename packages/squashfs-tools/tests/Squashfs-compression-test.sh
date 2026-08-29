#!/bin/bash

# We need rpmdev-vercmp
rpm -q rpmdevtools > /dev/null 2>&1 || (echo 'rpmdev-vercmp from rpmdevtools is needed to run this script, aborting (failed).'; exit 1)

# Define block sizes
blocks=(4K 1M)

# Define fill files
fill=(/dev/zero /dev/urandom)

# Define number of iterations
iter=5

# Define fragment sizes
frags=(0 1 2047 4095)

# Define test directory
testdir=/tmp/test-squashfs

# Define mount point
mp=${testdir}/mnt

# Define data directory
datadir=${testdir}/data

# Check for squashfs-tools version and set compression types to test
sqfsver=`rpm -q --qf '%{EVR}' squashfs-tools`
if rpmdev-vercmp 4.1 ${sqfsver} > /dev/null; [ $? == '11' ]; then
  ucomp=('gzip')
elif rpmdev-vercmp 4.2 ${sqfsver} > /dev/null; [ $? == '11' ]; then
  ucomp=(gzip lzo lzma)
elif rpmdev-vercmp 4.3-1 ${sqfsver} > /dev/null; [ $? == '11' ]; then
  ucomp=(gzip lzo lzma xz)
elif rpmdev-vercmp 4.3-21 ${sqfsver} > /dev/null; [ $? == '11' ]; then
  ucomp=(gzip lzo lzma xz lz4)
else
  ucomp=(gzip lzo lzma xz lz4 zstd)
fi

# Check for kernel verion and set mount test compression types
kernel=`uname -r`
if rpmdev-vercmp 2.6.36 ${kernel} > /dev/null; [ $? == '11' ]; then
  mcomp=('gzip')
elif rpmdev-vercmp 2.6.38 ${kernel} > /dev/null; [ $? == '11' ]; then
  mcomp=(gzip lzo)
elif rpmdev-vercmp 3.19 ${kernel} > /dev/null; [ $? == '11' ]; then
  mcomp=(gzip lzo xz)
elif rpmdev-vercmp 4.14 ${kernel} > /dev/null; [ $? == '11' ]; then
  mcomp=(gzip lzo xz lz4)
else
  mcomp=(gzip lzo xz lz4 zstd)
fi

# Check for uid 0 and print a warning if not
[ ${UID} -ne 0 ] && echo 'Mount tests will not be performed when not running as root'

# Check if test directory exists and make if not
[ -d ${testdir} ] || mkdir ${testdir}
[ -d ${testdir} ] || (echo "Unable to make '${testdir}', aborting (failed)."; exit 1)

# Check if mount point directory exists and make if not
[ -d ${mp} ] || mkdir ${mp}
[ -d ${mp} ] || (echo "Unable to make '${mp}', aborting (failed)."; exit 1)

# Check if data directory exists and make if not
if [ -d ${datadir} ]; then
  echo "Using existing data directory."
else
  echo "Building data directory."
  mkdir ${datadir}
  [ -d ${datadir} ] || (echo "Unable to make '${datadir}', aborting (failed)."; exit 1)
  for size in ${frags[*]}; do
    for file in ${fill[*]}; do
      dd if=${file} of=${datadir}/frag-`basename ${file}`-${size} bs=1 count=${size} > /dev/null 2>&1
    done
  done
  for size in ${blocks[*]}; do
    for ((count=1;${count}<=${iter};count++)); do
      for file in ${fill[*]}; do
        dd if=${file} of=${datadir}/file-`basename ${file}`-${size}-${count} bs=${size} count=${count} > /dev/null 2>&1
      done
    done
  done
  for size1 in ${frags[*]}; do
    for file1 in ${fill[*]}; do
      for size2 in ${blocks[*]}; do
        for ((count=1;${count}<=${iter};count++)); do
          for file2 in ${fill[*]}; do
            cat ${datadir}/file-`basename ${file2}`-${size2}-${count} ${datadir}/frag-`basename ${file1}`-${size1} > ${datadir}/combined-`basename ${file2}`-${size2}-${count}-`basename ${file1}`-${size1}
          done
        done
      done
    done
  done
fi

# Run unmounted tests
for comp in ${ucomp[*]}; do
  echo "Building squashfs image using ${comp} compression."
  if [ "${comp}" == gzip ]; then
    mksquashfs ${datadir} ${testdir}/sq.img || (echo "mksquashfs failed for ${comp} compression."; continue)
  else
    mksquashfs ${datadir} ${testdir}/sq.img -comp ${comp} || (echo "mksquashfs failed for ${comp} compression."; continue)
  fi
  echo "Testing unmounted extract using ${comp} compression."
  unsquashfs -d ${testdir}/sq ${testdir}/sq.img  || echo "unsquashfs failed for ${comp} compression."
  diff -r -q ${testdir}/sq ${datadir} || (echo "Extract test failed for ${comp} compression."; exit)
  rm -rf ${testdir}/sq
  if [ ${UID} == 0 ]; then
    for kern in ${mcomp[*]}; do
      if [ ${kern} == ${comp} ]; then
        echo "Testing mounted image using ${comp} compression."
        mount -r -o loop -t squashfs ${testdir}/sq.img ${mp} || echo "Mount failed.";
        diff -r -q ${mp} ${datadir} || echo "Mounted test failed for ${comp} compression."
        umount ${mp}
        break
      fi
    done
  fi
  rm -f ${testdir}/sq ${testdir}/sq.img
done
