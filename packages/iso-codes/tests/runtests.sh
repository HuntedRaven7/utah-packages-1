#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

NAME=iso-codes

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm ${NAME}
        rlShowPackageVersion ${NAME}
        rlRun -t -l "VERSION=$(rpm -q ${NAME} --queryformat='%{version}')" 0 "Get VERSION"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlFetchSrcForInstalled "${NAME}"
        rlRun "rpm --define '_topdir $tmp' -i *src.rpm"
        rlRun -t -l "mkdir BUILD" 0 "Creating BUILD directory"
        rlRun -t -l "rpmbuild --noclean --nodeps --define '_topdir $tmp' -bp $tmp/SPECS/*spec"
        if [ -d BUILD/${NAME}-${VERSION}-build ]; then
            rlRun -t -l "pushd BUILD/${NAME}-${VERSION}-build/${NAME}-v${VERSION}"
        else
            rlRun -t -l "pushd BUILD/${NAME}-v${VERSION}"
        fi
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "set -o pipefail"
	rlRun "ls data/iso*.json -l"
        rlRun "python3 bin/validate_json_data.py"
        rlRun "retval=$?"
        rlRun "echo Test return value is $retval"
        rlRun "ls data/iso*.json -l"
        rlRun "retval2=$?"
        rlRun "echo $retval2"
        rlRun "popd" 0
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd

