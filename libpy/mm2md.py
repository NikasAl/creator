#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys
import html

def extract_text(node):
    return node.get("TEXT", "").replace("\n", " ")

def extract_link(node):
    return node.get("LINK", "")

def extract_note(node):
    note_elem = node.find("richcontent[@TYPE='NOTE']")
    if note_elem is not None:
        # Простое извлечение текста из CDATA или текста
        return note_elem.text or ""
    return ""

def process_node(node, depth=0):
    text = extract_text(node)
    link = extract_link(node)
    note = extract_note(node)

    indent = "  " * depth
    line = f"{indent}- {text}"
    if link:
        line += f" [{link}]"
    print(line)

    if note.strip():
        note_lines = note.strip().split("\n")
        for nl in note_lines:
            print(f"{indent}  > {nl}")

    for child in node.findall("node"):
        process_node(child, depth + 1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 mm2md.py <файл.mm>")
        sys.exit(1)

    tree = ET.parse(sys.argv[1])
    root_node = tree.getroot().find("node")
    if root_node is not None:
        process_node(root_node)