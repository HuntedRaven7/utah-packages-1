#!/bin/sh
if [ "$#" -eq 0 ]; then
  echo "Usage: ./update-gcc.sh gcc/redhat/heads/gcc-NN-branch_commit_hash [git_reference_dir_to_speed_up]"
  exit 1
fi
export LC_ALL=C
if ! [ -f gcc.spec ]; then echo Must be run in the directory with gcc.spec file.; exit 1; fi
if [ -d gcc-dir.tmp ]; then echo gcc-dir.tmp already exists.; exit 1; fi
v=`sed -n 's/^%global gcc_version //p' gcc.spec`
p=`sed -n 's/^%global gitrev //p' gcc.spec`
h=$1
if [ "$#" -ge 2 ]; then
  git clone --dissociate --reference $2 https://gcc.gnu.org/git/gcc.git gcc-dir.tmp
else
  git clone https://gcc.gnu.org/git/gcc.git gcc-dir.tmp
fi
git --git-dir=gcc-dir.tmp/.git fetch origin $h
d=`date --iso | sed 's/-//g'`
cd gcc-dir.tmp
git diff $p..$h > P1
git log --format=%B `git log --format='%ae %H' $p..$h | awk '/^gccadmin@gcc.gnu.org/{print $2;exit 0}'`..$h > P2
diff -up /dev/null P2 >> P1
sed -n 's,^+[[:blank:]]\+PR \([a-z0-9+-]\+/[0-9]\+\)$,\1,p' P1 | sed 's/ - .*$//;s/[: ;.]//g' | LC_ALL=C sort -u -t / -k 1,1 -k 2,2n > P3
> P4
for i in `cat P3`; do if grep -F $i ../gcc.spec >/dev/null; then echo $i already recorded.; else echo $i >> P4; fi; done
case "$v" in
  *.0.*) echo "- update from trunk" > P5;;
  *) echo "- update from releases/gcc-`echo $v | sed 's/\..*$//'` branch" > P5;;
esac
echo `cat P4` | sed 's/ /, /g' | fold -w 71 -s | sed '1s/^/  - PRs /;2,$s/^/	/;s/, $/,/' >> P5
echo >> P5
cd ..
sed -i -e '/^%global gitrev /s/ [0-9a-f]\+$/ '$h'/;/^%global DATE /s/ [0-9]\+$/ '$d'/;/^%changelog$/r gcc-dir.tmp/P5' gcc.spec
git --git-dir=gcc-dir.tmp/.git archive --prefix=gcc-$v-$d/ $h | xz -9e > gcc-$v-$d.tar.xz
rm -rf gcc-dir.tmp
fedpkg new-sources gcc-$v-$d.tar.xz `sed 's/SHA512 (\(.*\)) = [0-9a-f]\+$/\1/' sources | grep -v '^gcc-'`
