# Copyright (c) 2020-2023 Khaled Hosny
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

NAME = Raqq

MAKEFLAGS := -sr
SHELL = bash

CONFIG = _config.yml
VERSION = $(shell python version.py $(CONFIG))
DIST = $(NAME)-$(VERSION)

SOURCEDIR = sources
SCRIPTDIR = scripts
FONTDIR = fonts
TESTDIR = tests
BUILDDIR = build

STYLES = Text # Display
OTF = $(STYLES:%=$(FONTDIR)/$(NAME)%.otf)
TTF = $(STYLES:%=$(FONTDIR)/$(NAME)%.ttf)
FEA = $(STYLES:%=$(SOURCEDIR)/$(NAME)%.fea)
JSON = $(TESTDIR)/shaping.json $(TESTDIR)/decomposition.json
HTML = $(STYLES:%=$(TESTDIR)/$(NAME)%.html)
FONTS = $(TTF) # $(OTF)
GLYPHDATA = $(SOURCEDIR)/GlyphData.xml

ARGS ?= 

.SECONDARY:

.PHONY: all dist

all: $(FONTS)
test: $(HTML)
update-test: $(JSON)
update-fea: $(FEA)

$(SOURCEDIR)/%.fea:
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-overhang-fea.py $(FONTDIR)/$(*F).ttf $@

$(FONTDIR)/%.otf: $(SOURCEDIR)/%.glyphs $(CONFIG) $(GLYPHDATA) $(SOURCEDIR)/%.fea
	$(info   BUILD  $(@F))
	python $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) $(ARGS)

$(FONTDIR)/%.ttf: $(SOURCEDIR)/%.glyphs $(CONFIG) $(GLYPHDATA) $(SOURCEDIR)/%.fea
	$(info   BUILD  $(@F))
	python $(SCRIPTDIR)/build.py $< $(VERSION) $@ --data=$(GLYPHDATA) $(ARGS)

$(TESTDIR)/%.html: $(FONTDIR)/%.ttf $(TESTDIR)/fontbakery.yml
	$(info   TEST   $(<F))
	fontbakery check-universal --config=$(TESTDIR)/fontbakery.yml \
                   fontbakery.profiles.shaping $< --html=$@ -l WARN &> /dev/null

$(TESTDIR)/decomposition.json: $(SOURCEDIR)/$(NAME)Text.glyphs $(FONTDIR)/$(NAME)Text.ttf
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-decomposition-test.py $@ $+

$(TESTDIR)/shaping.json: $(TESTDIR)/shaping.csv $(TTF)
	$(info   GEN    $(@F))
	python $(SCRIPTDIR)/update-shaping-test.py $@ $(NAME)Text $+

dist: all
	$(info   DIST   $(DIST).zip)
	install -Dm644 -t $(DIST) $(FONTS)
	install -Dm644 -t $(DIST) README.md
	install -Dm644 -t $(DIST) LICENSE
	zip -rq $(DIST).zip $(DIST)
