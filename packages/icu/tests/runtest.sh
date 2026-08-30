#!/bin/bash

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm "libicu"
        rlAssertRpm "libicu-devel"
        rlRun "g++ -g -O0  $(icu-config --cppflags --cxxflags --ldflags --ldflags-icuio) -o timezone-sample timezone-sample.cpp"
        rlRun "TmpDir=\`mktemp -d\`" 0 "Creating tmp directory"
        rlRun "cp timezone-sample $TmpDir"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "Run timezone-sample"
        rlRun -l "./timezone-sample" 0 "Running timezone tests"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

