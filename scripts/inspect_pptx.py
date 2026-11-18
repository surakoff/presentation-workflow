"""Read embedded fonts, explicit text fonts, and click actions from a PPTX."""

import argparse
from collections import Counter
import json
import posixpath
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RID = f'{{{NS["r"]}}}id'


def relationships(package: ZipFile, part: str) -> dict:
    folder, filename = posixpath.split(part)
    name = posixpath.join(folder, "_rels", filename + ".rels")
    try:
        contents = package.read(name)
    except KeyError:
        return {}
    return {node.get("Id"): node.attrib for node in ET.fromstring(contents)}


def inspect(path: Path) -> dict:
    fonts = Counter()
    actions = []
    with ZipFile(path) as package:
        part = "ppt/presentation.xml"
        presentation = ET.fromstring(package.read(part))
        rels = relationships(package, part)
        embedded = {
            node.find("p:font", NS).get("typeface"):
                [child.tag.rsplit("}", 1)[-1] for child in node if child.get(RID)]
            for node in presentation.findall(".//p:embeddedFont", NS)
        }
        slides = presentation.findall("p:sldIdLst/p:sldId", NS)
        for number, slide in enumerate(slides, 1):
            target = rels[slide.get(RID)]["Target"]
            part = (target.lstrip("/") if target.startswith("/")
                    else posixpath.normpath(posixpath.join("ppt", target)))
            source = ET.fromstring(package.read(part))
            for node in source.findall(".//a:rPr/a:latin", NS):
                name = node.get("typeface")
                if name and not name.startswith("+"):
                    fonts[name] += 1
            links = relationships(package, part)
            for node in source.findall(".//a:hlinkClick", NS):
                rid = node.get(RID)
                actions.append({
                    "slide": number,
                    "action": node.get("action"),
                    "target": links.get(rid, {}).get("Target"),
                    "missing_relationship": bool(rid and rid not in links),
                })
    embedded_names = {name.casefold() for name in embedded if name}
    return {
        "slides": len(slides),
        "embedded_font_parts": embedded,
        "font_subsetting": presentation.get("saveSubsetFonts") in {"true", "1"},
        "explicit_latin_run_fonts": dict(fonts),
        "explicit_families_absent_from_embedded_list": sorted(
            name for name in fonts if name.casefold() not in embedded_names
        ),
        "click_actions": actions,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    options = parser.parse_args()
    print(json.dumps(inspect(options.pptx), ensure_ascii=True, indent=2))
