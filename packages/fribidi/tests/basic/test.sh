#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "BUILD_PATH=$(rpm -q --qf '%{NAME}-%{VERSION}' fribidi)" 0 "Get the build path"
        if test -d $TMT_SOURCE_DIR/$BUILD_PATH; then
            for f in $TMT_SOURCE_DIR/$BUILD_PATH/test/*.input; do
                ref=${f/.input/.reference}
                cs=$(echo $f|cut -d_ -f2)
                name=$(basename $f)
                rlRun "fribidi -t -c $cs $f | tee output" 0 "Check $name for $cs"
                rlRun "diff -U 0 output $ref" 0 "Check diff for $name"
            done
        else
            rlDie "No build directory"
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
