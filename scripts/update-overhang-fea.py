#!/usr/bin/env python3
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

import itertools

import uharfbuzz as hb

THRESHOLD = 50
OVERHANGERS = ["ح", "ح\u200D", "ے"]

# To decrease lookup size, letters with similar glyph advances are grouped
# together, so ل is grouped with ٮ, and ط and ك are grouped with ص.
DUAL_JOINERS = ["ٮ", "ح", "س", "ص", "ع", "ڡ", "م", "ه"]

BUFFER = hb.Buffer()


def shape(font, text, direction="rtl", script="arab", features=None):
    BUFFER.clear_contents()
    BUFFER.add_str(text)
    BUFFER.direction = direction
    BUFFER.script = script
    BUFFER.flags = hb.BufferFlags.REMOVE_DEFAULT_IGNORABLES

    hb.shape(font, BUFFER, features)

    infos = BUFFER.glyph_infos
    positions = BUFFER.glyph_positions
    if BUFFER.direction == "rtl":
        infos.reverse()
        positions.reverse()

    glyphs = []
    advance = 0
    for info, pos in zip(infos, positions):
        glyph = font.glyph_to_string(info.codepoint)
        if glyph.startswith("behDotless-ar.init"):
            glyph = "@beh.init"
        elif glyph.startswith("behDotless-ar.medi"):
            glyph = "@beh.medi"
        elif glyph.startswith("sad-ar.init"):
            glyph = "@sad.init"
        elif glyph.startswith("sad-ar.medi"):
            glyph = "@sad.medi"
        elif glyph.startswith("hah-ar.init"):
            glyph = "@hah.init"
        elif glyph.startswith("hah-ar.medi"):
            glyph = "@hah.medi"
        elif glyph.startswith("seen-ar.medi"):
            glyph = "@seen.medi"
        glyphs.append(glyph)
        advance += pos.x_advance

    overhang = font.get_glyph_h_advance(infos[-1].codepoint)
    adj = overhang - advance

    # Round adjustment values to the nearest 10 units to reduce the number of
    # lookups.
    adj = round(adj / 10) * 10

    adj2 = None
    if glyphs[-1].startswith("yehbarree-ar.fina"):
        font2 = hb.Font(font.face)
        font2.set_variations({"MSHQ": 100})
        overhang2 = font2.get_glyph_h_advance(infos[-1].codepoint)
        adj2 = adj + (overhang2 - overhang)
        adj2 = f"(MSHQ=10:{adj} MSHQ=100:{adj2})"

    return glyphs, adj, adj2


def open_font(path):
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    font = hb.Font(face)
    return font


def main(args):
    font = open_font(args.font)

    rules = []
    for overhanger in OVERHANGERS:
        i = 0
        while True:
            sequence = [DUAL_JOINERS] + [DUAL_JOINERS] * i + [[overhanger]]
            found = False
            for string in itertools.product(*sequence):
                text = "".join(string)

                # If text has a hah followed by any other letter then yeh bari,
                # then the adjustment for the hah is enough and the rule here
                # is pointless.
                if "ح" in text and text.endswith("ے") and not text.endswith("حے"):
                    continue

                # If we have more than one hah, then the adjustment for the
                # first one is enough and the rule here is pointless.
                if text.count("ح") > 1:
                    continue

                glyphs, adj, adj2 = shape(font, text, features={"kern": False})
                if adj < THRESHOLD:
                    continue
                found = True

                if adj2 is not None:
                    adj = adj2

                match = glyphs[0]
                lookahead = "' ".join(glyphs[1:])
                rules.append(f"\tpos {match}' {adj} {lookahead}';")
            if not found:
                break
            i += 1

    with open(args.fea, "w") as fea:
        fea.write("# THIS FILE IS AUTO GENERATED, DO NOT EDIT\n\n")
        fea.write("lookup overhang {\n")
        fea.write("  lookupflag IgnoreMarks;\n")
        fea.write("\n".join(rules))
        fea.write("\n} overhang;\n\n")


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("font", type=Path, help="input font file path.")
    parser.add_argument("fea", type=Path, help="output .fea file path.")

    args = parser.parse_args()
    main(args)
