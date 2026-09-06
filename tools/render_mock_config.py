#!/usr/bin/env python3
"""Render Mock configuration targeting Hummingbird overlay on Fedora 44."""

from __future__ import annotations

import argparse
from pathlib import Path


def render_mock_config(stage_repo: str | None = None, root_name: str = "hummingbird-44-x86_64") -> str:
    stage_block = ""
    if stage_repo:
        stage_block = f"""
[stages]
name=stages
baseurl={stage_repo}
enabled=1
gpgcheck=0
priority=1
"""

    return f"""# Mock configuration targeting Hummingbird overlay on Fedora 44
config_opts['root'] = '{root_name}'
config_opts['target_arch'] = 'x86_64'
config_opts['legal_host_arches'] = ('x86_64',)
config_opts['chroot_setup_cmd'] = 'install @buildsys-build'
config_opts['package_manager'] = 'dnf5'
config_opts['rpmbuild_networking'] = False
config_opts['networking'] = False
# networking = False

config_opts['dnf.conf'] = \"\"\"
[main]
cachedir=/var/cache/dnf
keepcache=1
debuglevel=2
reposdir=
logfile=/var/log/dnf.log
retries=20
obsoletes=1
gpgcheck=0
assumeyes=1
syslog_ident=mock
syslog_device=
install_weak_deps=0
metadata_expire=0
best=1
releasever=44
tsflags=nodocs
{stage_block}
[public-hummingbird-x86_64-rpms]
name=public-hummingbird-x86_64-rpms
baseurl=https://packages.redhat.com/api/pulp-content/public-hummingbird/x86_64/
enabled=1
sslverify=1
gpgcheck=0
priority=10
zchunk=false
excludepkgs=libicu,icu

[fedora]
name=fedora
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-44&arch=x86_64
enabled=1
gpgcheck=0
priority=99
excludepkgs=ruby-default-gems,ruby3.3-default-gems,ruby3.4-default-gems,gpgme,qt6-qtbase

[updates]
name=updates
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f44&arch=x86_64
enabled=1
gpgcheck=0
priority=99
excludepkgs=ruby-default-gems,ruby3.3-default-gems,ruby3.4-default-gems,gpgme,qt6-qtbase
\"\"\"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-repo", help="URL or path to prior stage repo")
    parser.add_argument("--root-name", default="hummingbird-44-x86_64", help="mock root name")
    parser.add_argument("--output", type=Path, help="output file")
    args = parser.parse_args()

    content = render_mock_config(stage_repo=args.stage_repo, root_name=args.root_name)
    if args.output:
        args.output.write_text(content)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
