Name:           liblc3plus
Version:        1.7.1
Release:        1%{?dist}
Summary:        Low Complexity Communication Codec Plus (LC3plus)

License:        Fraunhofer LC3plus Patent Licensing
URL:            https://www.iis.fraunhofer.de/en/ff/amm/communication/lc3.html

Source0:        https://github.com/arkq/LC3plus/archive/v%{version}/%{name}-%{version}.tar.gz

# The upstream makefile builds an unversioned libLC3plus.so. Give it a proper
# soname so pipewire-libs-extra can link against a stable ABI.
Patch0:         %{name}-soname.patch
Patch1:         %{name}-cflags.patch

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  perl

%description
LC3plus is LC3's sibling, equipped with numerous additional functionalities.
While comprising all features of LC3, including high speech and audio quality,
LC3plus incorporates functionalities for transmission robustness, extremely
low-delay use cases and high-resolution audio transmission. To improve
robustness, LC3plus contains a very high-performance packet loss concealment
algorithm as well as forward error correction schemes such as channel coding or
redundancy frame modes.

%package devel
Summary: Development package for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}

%description devel
Files for development with %{name}.

%prep
%autosetup -p1 -n LC3plus-%{version}

find . -name "*.c" -exec chmod 644 {} \;
find . -name "*.h" -exec chmod 644 {} \;

%build
cd src/floating_point
%make_build LC3plus
%make_build libLC3plus.so

%install
mkdir -p %{buildroot}%{_bindir} \
    %{buildroot}%{_includedir} \
    %{buildroot}%{_libdir}
install -p -m 0755 src/floating_point/LC3plus %{buildroot}%{_bindir}/
install -p -m 0644 src/floating_point/lc3plus.h \
    src/floating_point/defines.h \
    %{buildroot}%{_includedir}/
cp -a src/floating_point/libLC3plus.so* %{buildroot}%{_libdir}/

%files
%doc Readme.txt
%{_bindir}/LC3plus
%{_libdir}/libLC3plus.so.1
%{_libdir}/libLC3plus.so.1.7.1

%files devel
%{_includedir}/lc3plus.h
%{_includedir}/defines.h
%{_libdir}/libLC3plus.so

%changelog
* Sun Aug 30 2026 Project Bluefin <bot@projectbluefin.io> - 1.7.1-1
- Initial Hummingbird-targeted build from upstream release
