# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# The options the devkit builds a console program with, each one tried on the
# compiler in use before it is given: a compiler or a linker that does not
# know one (another architecture, another system) builds without it, and
# `mdk check` then says what the program lacks.
#
#     CC     ?= gcc
#     CFLAGS ?= -O2
#     include $(MUN_DEVKIT)/mk/hardening.mk
#     $(CC) $(CFLAGS) $(MUN_HARDEN_CFLAGS) -c ...
#     $(CC) ... $(MUN_HARDEN_LDFLAGS) ...
#
# Include it after CC and CFLAGS are set: -D_FORTIFY_SOURCE needs an
# optimising build (the C library refuses it otherwise), so it is given only
# when CFLAGS optimise.
#
#   -fstack-protector-strong      a canary in every function with an array or
#                                 an address taken
#   -fstack-clash-protection      a large stack frame is touched page by page
#   -D_FORTIFY_SOURCE=3           the C library checks the sizes it can know
#   -mbranch-protection=standard  AArch64: BTI and return-address signing.
#                                 The linker marks the program only when every
#                                 object in it was built this way
#   -fPIE, -pie                   a position-independent executable
#   -z relro, -z now              the tables the loader fills become read-only
#                                 before the program runs
#   -z noexecstack                no code runs from the stack

mun_probe_source := int main(void) { return 0; }
mun_comma := ,
# $(call mun_cc_accepts,FLAGS): "yes" if a program compiles and links with them
# and without a warning.
mun_cc_accepts = $(shell printf '%s\n' '$(mun_probe_source)' | $(CC) -Werror $(1) -x c - -o /dev/null 2>/dev/null && echo yes)
mun_flag_if = $(if $(call mun_cc_accepts,$(1)),$(1))
# The compiler says whether it optimises by defining __OPTIMIZE__. Asked
# for its definitions, not with a conditional in a probe program: a '#' in
# a makefile is read differently by different versions of make.
mun_optimising := $(shell $(CC) $(CFLAGS) -dM -E -x c /dev/null 2>/dev/null | grep -q __OPTIMIZE__ && echo yes)

MUN_HARDEN_CFLAGS := $(call mun_flag_if,-fstack-protector-strong) \
                     $(call mun_flag_if,-fstack-clash-protection) \
                     $(if $(mun_optimising),-D_FORTIFY_SOURCE=3) \
                     $(call mun_flag_if,-mbranch-protection=standard) \
                     $(call mun_flag_if,-fPIE)
MUN_HARDEN_LDFLAGS := $(call mun_flag_if,-pie) \
                      $(call mun_flag_if,-Wl$(mun_comma)-z$(mun_comma)relro) \
                      $(call mun_flag_if,-Wl$(mun_comma)-z$(mun_comma)now) \
                      $(call mun_flag_if,-Wl$(mun_comma)-z$(mun_comma)noexecstack)
