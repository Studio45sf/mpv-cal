#!make

.DEFAULT_GOAL := help

.DELETE_ON_ERROR:

MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables
MAKEFLAGS += --check-symlink-times

# colors
gray := $(shell printf '\e[0;30m')
green := $(shell printf '\e[0;32m')
reset := $(shell printf '\033[0m')

pip_prefix := > >(sed 's/^/'"$(green)[pip]$(reset)"' /') 2> >(sed 's/^/'"$(green)[pip]$(reset)"' /' >&2)

PS4 := $(gray)[make] $(reset)

export PS4

set_bash_x_arg := x
set_bash_x := && set -x
verbose := --verbose
MAKEFLAGS += --debug --trace $(verbose)

no_shell_debug := { set +x; } 2>/dev/null
set_ps4 := $(no_shell_debug) && export PS4="$(PS4)" $(set_bash_x) &&

SHELL := /bin/bash
.SHELLFLAGS := --noprofile --norc -o pipefail -eu$(set_bash_x_arg) -c

help:  ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(cyan)$(reset)\n"} /^[$$()% a-zA-Z_-]+:.*?##/ { printf "  $(cyan)%-15s$(reset) %s\n", $$1, $$2        } /^##@/ { printf "\n\033[1m%s$(reset)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

print-%:  ## Print the value of a variable, e.g. make print-PREFIX
	echo '$($*)'

# capture errors from subprocesses and fail immediately
# NOTE: this is emulating this better alternative that only it only works in make >v4
# $(shell $(1))$(if $(filter-out 0,$(.SHELLSTATUS)),$(error Shell command failed: $(1)))
define safe-shell
$(shell $(set_ps4) $(1) || { echo >&2 "Shell command failed: $(1)"; kill $$PPID; })
endef

package_name := $(call safe-shell,grep '^name =' setup.cfg | head -1 | awk -F ' = ' '{print $$NF}' || :)

PREFIX ?= $(HOME)/.local
VENV_ROOT ?= $(PREFIX)
VIRTUAL_ENV := $(abspath $(VENV_ROOT))

SYS_PATH ?= /usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/bin
PATH := $(VIRTUAL_ENV)/bin:$(PREFIX)/bin:$(HOME)/.cargo/bin:$(HOME)/go/bin:$(SYS_PATH)
XDG_CONFIG_HOME ?= ~/.config

export PATH
export VIRTUAL_ENV
export XDG_CONFIG_HOME

# prevent pip from installing executables out-of-tree, which by default is ~/.local
PYTHONUSERBASE ?= $(VIRTUAL_ENV)

pip := $(VENV_ROOT)/bin/pip

activate_venv := { ! test -f $(VENV_ROOT)/bin/activate || . $(VENV_ROOT)/bin/activate; }

ifeq ($(PREFIX),$(VENV_ROOT))
pip_uninstall_user_args := --break-system-packages
pip_install_user_args := --user $(pip_uninstall_user_args)
else
pip_uninstall_user_args :=
pip_install_user_args :=
endif

$(pip): setup.cfg
	mkdir -p $(VENV_ROOT) \
	&& { echo $(VENV_ROOT) | grep -q $(PREFIX) || { test -f $(VENV_ROOT)/.gitignore || echo '*' > $(VENV_ROOT)/.gitignore; }; } \
	&& { echo $(VENV_ROOT) | grep -q $(PREFIX) || { python -m venv $(VENV_ROOT) $(pip_prefix); }; } \
	&& $(activate_venv) \
	&& pip install $(pip_install_user_args) -U pip wheel setuptools maturin $(pip_prefix) \
	&& test -f $(pip) \
	&& touch $(pip)

pip: $(pip)  ## upgrade pip

.PHONY: pip

self_package_pattern := $(VENV_ROOT)/lib/python*/site-packages/__editable__.$(package_name)*.pth
self_package := $(call safe-shell,echo $(self_package_pattern) | xargs -n1 | grep -v '\-bak' | tail -1)

$(self_package): $(pip)
	$(activate_venv) \
	&& pip uninstall $(pip_uninstall_user_args) -y $(package_name) \
	&& pip install $(pip_install_user_args) --no-build-isolation --no-clean --prefer-binary --editable .[test] $(pip_prefix) \
	&& test -f $(self_package) \
	&& touch $(self_package)

venv: $(self_package)  ## build the virtualenv and editable install, defaults to installing into ~/.local

.PHONY: venv

nice := nice -n 19 ionice -c3
safe_xargs := xargs --no-run-if-empty
nice_xargs := $(safe_xargs) -0 $(nice)
python := $(call safe-shell,which python | xargs readlink -f)
git_files_null := $(nice) git ls-files -z --
map_py_exec := $(git_files_null) "*.py" | $(nice_xargs)
map_python := $(map_py_exec) $(python) -m
map_git_files := $(git_files_null) "*" | $(nice_xargs)
map_symlinks := $(nice) find . -type l -print0 | $(nice_xargs)
map_executables := $(nice) find . -type f -executable -print0 | $(nice_xargs)
map_shell_scripts := $(nice) git ls-files | grep -v -P '.*\.py$$' | $(safe_xargs) grep -El '\#!.*(bash|zsh|sh|dash)$$' | $(safe_xargs) $(nice)
map_py_tests := $(nice) git ls-files | grep -P '(^|/)tests/.+\.py$$' | $(safe_xargs) $(nice)
map_requirements_txt := { $(nice) git ls-files | grep -P ".*requirements.*\.txt$$" || :; } | $(safe_xargs) $(nice)
map_setup_cfg := { $(nice) git ls-files | grep -P "^setup\.cfg$$" || :; } | $(safe_xargs) $(nice)

format: $(self_package)  ## auto-format the code
	$(activate_venv) \
	&& $(map_setup_cfg) setup-cfg-fmt \
	&& $(map_python) isort \
	&& $(map_python) black \
	&& $(map_git_files) end-of-file-fixer \
	&& $(map_git_files) trailing-whitespace-fixer \
	&& $(map_git_files) mixed-line-ending \
	&& $(map_python) pyupgrade --py39-plus \
	&& $(map_requirements_txt) requirements-txt-fixer \
	&& $(git_files_null) "*.json" | $(nice_xargs) check-json \
	&& $(git_files_null) "*.yaml" | $(nice_xargs) check-yaml \
	&& $(git_files_null) "*.yml" | $(nice_xargs) check-yaml \
	&& $(git_files_null) "*.toml" | $(nice_xargs) check-toml

.PHONY: format

lint: $(self_package)  ## lint the code
	$(activate_venv) \
	&& $(map_python) flake8 \
	&& $(map_python) pylint --jobs=0 \
	&& $(map_python) pydocstyle \
	&& $(map_python) eradicate \
	&& $(map_python) bandit -c pyproject.toml \
	&& $(map_py_exec) check-docstring-first \
	&& $(map_py_exec) debug-statement-hook \
	&& $(map_py_tests) name-tests-test \
	&& $(map_executables) check-executables-have-shebangs \
	&& $(map_git_files) check-merge-conflict \
	&& $(map_symlinks) check-symlinks \
	&& vulture \
	&& $(map_shell_scripts) shellcheck \
	&& $(map_python) mypy \
	&& $(map_python) pyright

.PHONY: lint

install: $(self_package)  ## install the package and services, including system dependencies
	MPV_CALENDAR_NO_PIP=1 mpv-calendar-remote-installer
