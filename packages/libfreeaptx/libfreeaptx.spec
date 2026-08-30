Name:           libfreeaptx
Version:        0.2.2
Release:        1%{?dist}
Summary:        Free implementation of Audio Processing Technology codec (aptX)

License:        LGPLv2+
URL:            https://github.com/regularhunter/%{name}

Source0:        https://github.com/regularhunter/%{name}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  make

%description
This is an Open Source implementation of Audio Processing Technology codec
(aptX). This codec is mainly used in Bluetooth A2DP profile.

There is support for aptX and aptX HD codec variants. Both variants operates on
a raw 24 bit signed stereo audio samples. aptX provides fixed compress ratio 2:1
and aptX HD fixed compress ratio 4:1.

%package devel
Summary:    Development files for %{name}
Requires:   %{name}%{?_isa} = %{version}-%{release}

%description devel
The %{name}-devel package contains libraries and header files for developing
applications that use %{name}.

%package tools
Summary:    %{name} encoder and decoder utilities
Requires:   %{name}%{?_isa} = %{version}-%{release}

%description tools
The %{name}-tools package contains command line encoder and decoder utilities.

%prep
%autosetup -n %{name}-%{version}

%build
%make_build LDFLAGS="%{build_ldflags}" "CFLAGS=%{build_cflags}"

%install
%make_install PREFIX=%{_prefix} LIBDIR=%{_lib}

%files
%license COPYING
%{_libdir}/%{name}.so.0
%{_libdir}/%{name}.so.%{version}

%files devel
%{_includedir}/freeaptx.h
%{_libdir}/%{name}.so
%{_libdir}/pkgconfig/%{name}.pc

%files tools
%doc README
%{_bindir}/freeaptxenc
%{_bindir}/freeaptxdec

%changelog
* Sun Aug 30 2026 Project Bluefin <bot@projectbluefin.io> - 0.2.2-1
- Initial Hummingbird-targeted build from upstream release
