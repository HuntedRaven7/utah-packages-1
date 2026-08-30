#!/bin/bash
#
# Samba package dependency structure verification
#
# This test ensures that the samba library package dependencies don't regress.
# The expected hierarchy is:
#
#   samba-core-libs    (no samba-*-libs dependencies)
#        ^
#        |
#   samba-ndr-libs     (depends on samba-core-libs only)
#        ^
#        |
#   samba-client-libs  (depends on samba-core-libs + samba-ndr-libs)
#
#   libwbclient        (no samba-*-libs dependencies - only links to libc)
#
#   samba-client       (depends on samba-client-libs, NOT samba-libs)
#   libsmbclient       (depends on samba-client-libs, NOT samba-libs)
#
# NOTE: This test checks RESOLVED dependencies, not just explicit Requires.
# A library requirement like 'libfoo.so' is resolved to the package that
# provides it, ensuring we catch indirect dependencies.
#

set -e

ERRORS=0

# Get all packages that a package depends on (resolved)
# This resolves library deps like 'libfoo.so' to actual package names
get_resolved_deps() {
    local pkg="$1"

    rpm --query --requires "$pkg" 2>/dev/null | while read -r req; do
        # Skip rpmlib and config requirements
        [[ "$req" =~ ^rpmlib ]] && continue
        [[ "$req" =~ ^config ]] && continue
        [[ "$req" =~ ^/ ]] && continue

        # Get the package that provides this requirement
        provider=$(rpm --query --whatprovides "$req" 2>/dev/null | head -1)
        if [ -n "$provider" ] && [ "$provider" != "no package provides $req" ]; then
            # Extract just the package name (remove version-release.arch)
            echo "${provider%%-[0-9]*}"
        fi
    done | sort -u
}

# Check that a package does NOT depend on packages matching a pattern
# This checks RESOLVED dependencies (what packages actually get pulled in)
check_no_resolved_dep() {
    local pkg="$1"
    local pattern="$2"
    local description="$3"

    if ! rpm --query "$pkg" &>/dev/null; then
        echo "SKIP: $pkg not installed"
        return 0
    fi

    local bad_deps
    # Exclude the package itself from the check
    bad_deps=$(get_resolved_deps "$pkg" | grep -v "^${pkg}$" | grep -E "$pattern" || true)

    if [ -n "$bad_deps" ]; then
        echo "FAIL: $pkg depends on $description"
        echo "  Found: $bad_deps"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    echo "PASS: $pkg does not depend on $description"
    return 0
}

# Check that a package DOES depend on a specific package
check_has_resolved_dep() {
    local pkg="$1"
    local expected="$2"

    if ! rpm --query "$pkg" &>/dev/null; then
        echo "SKIP: $pkg not installed"
        return 0
    fi

    if get_resolved_deps "$pkg" | grep -qF "$expected"; then
        echo "PASS: $pkg depends on $expected"
        return 0
    fi
    echo "FAIL: $pkg does not depend on $expected"
    ERRORS=$((ERRORS + 1))
    return 1
}

echo "=== Samba Package Dependency Checks ==="
echo ""
echo "Checking resolved dependencies (library deps resolved to packages)"
echo ""

# 1. samba-core-libs must NOT depend on any samba-*-libs packages
echo "--- samba-core-libs ---"
check_no_resolved_dep samba-core-libs "^samba-.*-libs$" "any samba*-libs package"

echo ""

# 2. samba-ndr-libs must depend on samba-core-libs
#    but NOT samba-client-libs or samba-libs
echo "--- samba-ndr-libs ---"
check_has_resolved_dep samba-ndr-libs "samba-core-libs"
check_no_resolved_dep samba-ndr-libs "^samba-client-libs$" "samba-client-libs"
check_no_resolved_dep samba-ndr-libs "^samba-libs$" "samba-libs"

echo ""

# 3. samba-client-libs must depend on samba-core-libs and samba-ndr-libs
#    but NOT samba-libs
echo "--- samba-client-libs ---"
check_has_resolved_dep samba-client-libs "samba-core-libs"
check_has_resolved_dep samba-client-libs "samba-ndr-libs"
check_no_resolved_dep samba-client-libs "^samba-libs$" "samba-libs"

echo ""

# 4. libwbclient must NOT depend on any samba-*-libs packages
echo "--- libwbclient ---"
check_no_resolved_dep libwbclient "^samba-.*-libs$" "any samba*-libs package"

echo ""

# 5. samba-client must depend on samba-client-libs but NOT samba-libs
#    (client tools should not pull in server libraries)
echo "--- samba-client ---"
check_has_resolved_dep samba-client "samba-client-libs"
check_no_resolved_dep samba-client "^samba-libs$" "samba-libs"

echo ""

# 6. libsmbclient must depend on samba-client-libs but NOT samba-libs
#    (SMB client library should not pull in server libraries)
echo "--- libsmbclient ---"
check_has_resolved_dep libsmbclient "samba-client-libs"
check_no_resolved_dep libsmbclient "^samba-libs$" "samba-libs"

echo ""

# 7. libldb must NOT depend on any samba-*-libs packages
#    (libldb is a standalone database library)
echo "--- libldb ---"
check_no_resolved_dep libldb "^samba-.*-libs$" "any samba*-libs package"

echo ""

# 8. samba-libs must NOT depend on samba-dc-libs
#    (server libraries should not pull in DC-specific libraries)
echo "--- samba-libs ---"
check_no_resolved_dep samba-libs "^samba-dc-libs$" "samba-dc-libs"

echo ""
echo "=== Summary ==="

if [ $ERRORS -gt 0 ]; then
    echo "FAILED: $ERRORS dependency check(s) failed"
    exit 1
fi

echo "All dependency checks passed"
exit 0
