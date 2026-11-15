#!/usr/bin/env python3
"""Preview ZMK keymap layers as terminal tables or SVG images.

Examples:
    python3 tools/keymap.py                 # fzf picker, or all layers when piped
    python3 tools/keymap.py BASE            # one layer
    python3 tools/keymap.py --all           # every layer
    python3 tools/keymap.py --list          # layer names only
    python3 tools/keymap.py --combos        # combo table
    python3 tools/keymap.py --all --svg     # write SVGs to docs/images/layers
    python3 tools/keymap.py BASE --chafa    # render an SVG in the terminal

The parser is dependency-free and only understands the devicetree subset used
by ZMK keymaps: #defines, layers, bindings and combos.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEYMAP = ROOT / "config" / "totem.keymap"
DEFAULT_SVG_DIR = ROOT / "docs" / "images" / "layers"

KEY_WIDTH = 8
KEY_INNER = 6
SPLIT_GAP = 3

# ---------------------------------------------------------------------------
# Small display helpers
# ---------------------------------------------------------------------------

MODIFIER_SYMBOLS = {
    "LS": "shift",
    "RS": "shift",
    "LSHIFT": "shift",
    "RSHIFT": "shift",
    "LSHFT": "shift",
    "RSHFT": "shift",
    "LEFT_SHIFT": "shift",
    "RIGHT_SHIFT": "shift",
    "LC": "ctrl",
    "RC": "ctrl",
    "LCTRL": "ctrl",
    "RCTRL": "ctrl",
    "LCTL": "ctrl",
    "RCTL": "ctrl",
    "LEFT_CTRL": "ctrl",
    "RIGHT_CTRL": "ctrl",
    "LA": "alt",
    "RA": "alt",
    "LALT": "alt",
    "RALT": "alt",
    "LEFT_ALT": "alt",
    "RIGHT_ALT": "alt",
    "LG": "meta",
    "RG": "meta",
    "LGUI": "meta",
    "RGUI": "meta",
    "LWIN": "meta",
    "RWIN": "meta",
    "LEFT_WIN": "meta",
    "RIGHT_WIN": "meta",
    "LEFT_COMMAND": "meta",
    "RIGHT_COMMAND": "meta",
}

# Modifiers that get a compact single-letter form when stacked on one key.
MODIFIER_STACK_ORDER = ("shift", "ctrl", "alt", "meta")

KEYCODE_NAMES = {
    "NUMBER_0": "0",
    "NUMBER_1": "1",
    "NUMBER_2": "2",
    "NUMBER_3": "3",
    "NUMBER_4": "4",
    "NUMBER_5": "5",
    "NUMBER_6": "6",
    "NUMBER_7": "7",
    "NUMBER_8": "8",
    "NUMBER_9": "9",
    "N0": "0",
    "N1": "1",
    "N2": "2",
    "N3": "3",
    "N4": "4",
    "N5": "5",
    "N6": "6",
    "N7": "7",
    "N8": "8",
    "N9": "9",
    "EXCLAMATION": "!",
    "AT_SIGN": "@",
    "POUND": "#",
    "HASH": "#",
    "DOLLAR": "$",
    "PERCENT": "%",
    "CARET": "^",
    "AMPERSAND": "&",
    "ASTERISK": "*",
    "LEFT_PARENTHESIS": "(",
    "RIGHT_PARENTHESIS": ")",
    "MINUS": "-",
    "UNDERSCORE": "_",
    "EQUAL": "=",
    "PLUS": "+",
    "LEFT_BRACKET": "[",
    "RIGHT_BRACKET": "]",
    "BACKSLASH": "\\",
    "BSLH": "\\",
    "PIPE": "|",
    "GRAVE": "`",
    "TILDE": "~",
    "SEMI": ";",
    "SEMICOLON": ";",
    "COLON": ":",
    "SQT": "'",
    "SINGLE_QUOTE": "'",
    "APOSTROPHE": "'",
    "DQT": '"',
    "DOUBLE_QUOTE": '"',
    "COMMA": ",",
    "DOT": ".",
    "PERIOD": ".",
    "SLASH": "/",
    "FSLH": "/",
    "QUESTION": "?",
    "LEFT_BRACE": "{",
    "RIGHT_BRACE": "}",
    "BACKTICK": "`",
    "LEFT_ANGLE_BRACKET": "<",
    "RIGHT_ANGLE_BRACKET": ">",
    "SPACE": "SPC",
    "ENTER": "ENT",
    "RET": "ENT",
    "TAB": "TAB",
    "BSPC": "BSPC",
    "BACKSPACE": "BSPC",
    "DEL": "DEL",
    "DELETE": "DEL",
    "ESC": "ESC",
    "ESCAPE": "ESC",
    "HOME": "HOME",
    "END": "END",
    "PG_UP": "PGUP",
    "PAGE_UP": "PGUP",
    "PG_DN": "PGDN",
    "PAGE_DOWN": "PGDN",
    "UP": "↑",
    "DOWN": "↓",
    "LEFT": "←",
    "RIGHT": "→",
    "PRINTSCREEN": "PRTSC",
    "PRINT_SCREEN": "PRTSC",
    "CAPS": "CAPS",
    "CAPS_LOCK": "CAPS",
    "MENU": "MENU",
    "C_VOLUME_UP": "VOL+",
    "C_VOL_UP": "VOL+",
    "C_VOLUME_DOWN": "VOL-",
    "C_VOL_DN": "VOL-",
    "C_MUTE": "MUTE",
    "C_PLAY_PAUSE": "PLAY",
    "C_NEXT": "NEXT",
    "C_PREV": "PREV",
    "C_STOP": "STOP",
    "C_EJECT": "EJECT",
    "C_BRIGHTNESS_UP": "BRI+",
    "C_BRIGHTNESS_DOWN": "BRI-",
    "C_AL_CALC": "CALC",
    "C_AC_SEARCH": "SRCH",
    "C_AC_HOME": "HOME",
    "C_AC_BACK": "BACK",
    "C_AC_FORWARD": "FWD",
    "C_AC_REFRESH": "REFR",
    "C_AC_BOOKMARKS": "BOOK",
    "C_AC_STOP": "STOP",
    "C_AC_NEXT": "NEXT",
    "C_AC_PREV": "PREV",
    "KP_PLUS": "KP+",
    "KP_MINUS": "KP-",
    "KP_MULTIPLY": "KP*",
    "KP_DIVIDE": "KP/",
    "KP_ENTER": "KP↵",
    "KP_DOT": "KP.",
    "KP_EQUAL": "KP=",
    "KP_COMMA": "KP,",
}

for _index in range(1, 25):
    KEYCODE_NAMES[f"F{_index}"] = f"F{_index}"

MODIFIER_RE = re.compile(
    r"^(" + "|".join(sorted(MODIFIER_SYMBOLS, key=len, reverse=True)) + r")\((.*)\)$"
)
BEHAVIOR_RE = re.compile(r"&([A-Za-z0-9_]+)\s*(.*)", re.S)


def display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def fit_label(text: str, width: int = KEY_INNER) -> str:
    text = " ".join(text.split())
    if display_width(text) <= width:
        return text
    compact = text.replace(" ", "")
    if display_width(compact) <= width:
        return compact
    result = ""
    for char in compact:
        if display_width(result + char) > width - 1:
            break
        result += char
    return result + "…"


def center_label(text: str, width: int = KEY_INNER) -> str:
    text = fit_label(text, width)
    padding = max(0, width - display_width(text))
    left = padding // 2
    right = padding - left
    return " " * left + text + " " * right


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@dataclass
class KeyLabel:
    main: str
    sub: str = ""
    kind: str = "normal"


@dataclass
class Layer:
    index: int
    node: str
    label: str | None
    rows: list[list[str]]
    name: str = ""

    @property
    def bindings(self) -> list[str]:
        return [binding for row in self.rows for binding in row]


@dataclass
class Combo:
    name: str
    bindings: list[str]
    positions: list[int]


@dataclass
class Keymap:
    path: Path
    defines: dict[str, int]
    layers: list[Layer] = field(default_factory=list)
    combos: list[Combo] = field(default_factory=list)

    def resolve_layer(self, argument: str) -> Layer | None:
        argument = argument.strip()
        if argument.isdigit():
            index = int(argument)
            return self.layers[index] if 0 <= index < len(self.layers) else None
        if argument in self.defines:
            index = self.defines[argument]
            if 0 <= index < len(self.layers):
                return self.layers[index]
        lowered = argument.lower()
        for layer in self.layers:
            names = {layer.name.lower(), layer.node.lower()}
            if layer.label:
                names.add(layer.label.lower())
            if lowered in names:
                return layer
        return None


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def find_block(text: str, brace_index: int) -> tuple[str, int]:
    """Return the contents of a {...} block and the index just after its close."""
    depth = 0
    for index in range(brace_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_index + 1 : index], index + 1
    raise ValueError("unbalanced braces in keymap")


def iter_nodes(text: str):
    """Yield (node_name, node_body) for direct child nodes of a block."""
    pattern = re.compile(r"([A-Za-z_][\w-]*)\s*\{")
    position = 0
    while True:
        match = pattern.search(text, position)
        if not match:
            return
        brace_index = match.end() - 1
        body, end = find_block(text, brace_index)
        yield match.group(1), body
        position = end


def extract_angle(body: str, key: str) -> str | None:
    match = re.search(rf"{re.escape(key)}\s*=\s*<([^>]*)>", body, re.S)
    return match.group(1) if match else None


def extract_label(body: str) -> str | None:
    match = re.search(r'label\s*=\s*"([^"]*)"', body)
    return match.group(1) if match else None


def split_binding_rows(bindings_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in bindings_text.splitlines():
        tokens = [token.strip() for token in re.findall(r"&[^&<>]+", line)]
        tokens = [token for token in tokens if token]
        if tokens:
            rows.append(tokens)
    if len(rows) == 1 and len(rows[0]) == 38:
        flat = rows[0]
        rows = [flat[0:10], flat[10:20], flat[20:32], flat[32:38]]
    return rows


def parse_keymap(path: Path) -> Keymap:
    text = strip_comments(path.read_text(encoding="utf-8"))
    defines = {
        match.group(1): int(match.group(2))
        for match in re.finditer(r"#define\s+(\w+)\s+(\d+)\b", text)
    }

    keymap = Keymap(path=path, defines=defines)

    keymap_match = re.search(r"\bkeymap\s*\{", text)
    if not keymap_match:
        raise ValueError(f"no keymap block found in {path}")
    keymap_body, _ = find_block(text, keymap_match.end() - 1)

    for node, body in iter_nodes(keymap_body):
        bindings_text = extract_angle(body, "bindings")
        if bindings_text is None:
            continue
        rows = split_binding_rows(bindings_text)
        if not rows:
            continue
        keymap.layers.append(
            Layer(
                index=len(keymap.layers),
                node=node,
                label=extract_label(body),
                rows=rows,
            )
        )

    combos_match = re.search(r"\bcombos\s*\{", text)
    if combos_match:
        combos_body, _ = find_block(text, combos_match.end() - 1)
        for node, body in iter_nodes(combos_body):
            bindings_text = extract_angle(body, "bindings")
            positions_text = extract_angle(body, "key-positions")
            if bindings_text is None or positions_text is None:
                continue
            bindings = [
                token.strip()
                for token in re.findall(r"&[^&<>]+", bindings_text)
                if token.strip()
            ]
            positions = [int(value) for value in re.findall(r"\d+", positions_text)]
            keymap.combos.append(Combo(node, bindings, positions))

    define_by_index: dict[int, str] = {}
    for name, index in defines.items():
        if 0 <= index < len(keymap.layers):
            define_by_index.setdefault(index, name)

    for layer in keymap.layers:
        layer.name = (
            layer.label
            or define_by_index.get(layer.index)
            or layer.node.replace("_", " ").title()
        )

    return keymap


# ---------------------------------------------------------------------------
# Binding formatting
# ---------------------------------------------------------------------------


def split_binding(token: str) -> tuple[str, list[str]]:
    token = token.strip()
    match = BEHAVIOR_RE.match(token)
    if not match:
        return "", []
    behavior = match.group(1)
    rest = match.group(2).strip()
    return behavior, split_arguments(rest)


def split_arguments(text: str) -> list[str]:
    arguments: list[str] = []
    current = ""
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
            current += char
        elif char == ")":
            depth = max(0, depth - 1)
            current += char
        elif char.isspace() and depth == 0:
            if current:
                arguments.append(current)
                current = ""
        else:
            current += char
    if current:
        arguments.append(current)
    return arguments


def parse_modifiers(keycode: str) -> tuple[list[str], str]:
    """Split nested modifiers off a keycode, outermost first.

    ``LS(RA(EQUAL))`` -> ``(["shift", "alt"], "EQUAL")``.
    """
    modifiers: list[str] = []
    remaining = keycode.strip()
    while True:
        match = MODIFIER_RE.match(remaining)
        if not match:
            break
        modifier, inner = match.groups()
        modifiers.append(MODIFIER_SYMBOLS[modifier])
        remaining = inner.strip()
    return modifiers, remaining


def modifier_label(modifiers: list[str]) -> str:
    """Full word for a single modifier, first-letter codes when stacked."""
    if not modifiers:
        return ""
    if len(modifiers) == 1:
        return modifiers[0]
    return "+".join(modifier[0].upper() for modifier in modifiers)


def modifier_legend() -> str:
    return "  ".join(f"{word[0].upper()} = {word}" for word in MODIFIER_STACK_ORDER)


def keycode_display(keycode: str) -> str:
    keycode = keycode.strip()
    if not keycode:
        return "·"
    if keycode in MODIFIER_SYMBOLS:
        return MODIFIER_SYMBOLS[keycode]
    if keycode in KEYCODE_NAMES:
        return KEYCODE_NAMES[keycode]
    if len(keycode) == 1:
        return keycode.upper()
    return fit_label(keycode.replace("_", " "))


def keycode_kind(keycode: str) -> str:
    if keycode.strip().startswith("C_"):
        return "media"
    return "normal"


def layer_short(keymap: Keymap, argument: str) -> str:
    layer = keymap.resolve_layer(argument)
    if layer:
        return fit_label(layer.name)
    return fit_label(argument.replace("_", " "))


def format_binding(token: str, keymap: Keymap) -> KeyLabel:
    behavior, arguments = split_binding(token)
    if not behavior:
        return KeyLabel(fit_label(token), kind="normal")

    if behavior == "kp":
        keycode = arguments[0] if arguments else ""
        modifiers, base = parse_modifiers(keycode)
        return KeyLabel(
            keycode_display(base),
            modifier_label(modifiers),
            kind=keycode_kind(base),
        )

    if behavior == "mt":
        if len(arguments) >= 2:
            modifiers, base = parse_modifiers(arguments[0])
            modifier = modifier_label(modifiers) or keycode_display(base)
            tap_modifiers, tap_base = parse_modifiers(arguments[1])
            tap = keycode_display(tap_base)
            if tap_modifiers:
                tap = f"{tap} {modifier_label(tap_modifiers)}"
            return KeyLabel(modifier, tap, kind="mod")
        return KeyLabel("MT", kind="mod")

    if behavior == "lt":
        if len(arguments) >= 2:
            return KeyLabel(
                layer_short(keymap, arguments[0]),
                keycode_display(arguments[1]),
                kind="layer",
            )
        return KeyLabel("LT", kind="layer")

    if behavior == "mo":
        layer = layer_short(keymap, arguments[0]) if arguments else "MO"
        return KeyLabel(layer, "MO", kind="layer")

    if behavior == "to":
        layer = layer_short(keymap, arguments[0]) if arguments else "TO"
        return KeyLabel(fit_label("→" + layer), kind="layer")

    if behavior == "tog":
        layer = layer_short(keymap, arguments[0]) if arguments else "TOG"
        return KeyLabel(layer, "TOG", kind="layer")

    if behavior in {"trans", "none"}:
        return KeyLabel("·", kind="trans")

    if behavior == "bt":
        command = arguments[0] if arguments else ""
        if command == "BT_SEL" and len(arguments) > 1:
            return KeyLabel(f"BT{arguments[1]}", kind="media")
        if command == "BT_CLR":
            return KeyLabel("BT CLR", kind="media")
        if command == "BT_CLR_ALL":
            return KeyLabel("BT CLR", "ALL", kind="media")
        if command == "BT_PRV":
            return KeyLabel("BT ‹", kind="media")
        if command == "BT_NXT":
            return KeyLabel("BT ›", kind="media")
        if command == "BT_DISC":
            return KeyLabel("BT DSC", kind="media")
        return KeyLabel(fit_label("BT " + command.replace("BT_", "")), kind="media")

    if behavior == "out":
        command = arguments[0] if arguments else ""
        outputs = {"OUT_USB": "USB", "OUT_BLE": "BLE", "OUT_TOG": "OUT"}
        return KeyLabel(outputs.get(command, "OUT"), kind="media")

    if behavior == "mkp":
        command = arguments[0] if arguments else ""
        return KeyLabel(fit_label(command.replace("MOVE_", "")), kind="mouse")

    if behavior == "mmv":
        command = arguments[0] if arguments else ""
        moves = {
            "MOVE_LEFT": "←",
            "MOVE_DOWN": "↓",
            "MOVE_UP": "↑",
            "MOVE_RIGHT": "→",
        }
        return KeyLabel(moves.get(command, "MMV"), kind="mouse")

    if behavior == "msc":
        command = arguments[0] if arguments else ""
        scrolls = {
            "SCRL_UP": "SCRL↑",
            "SCRL_DOWN": "SCRL↓",
            "SCRL_LEFT": "SCRL←",
            "SCRL_RIGHT": "SCRL→",
        }
        return KeyLabel(scrolls.get(command, "SCRL"), kind="mouse")

    if behavior == "bootloader":
        return KeyLabel("BOOT", kind="normal")
    if behavior in {"sys_reset", "reset"}:
        return KeyLabel("RESET", kind="normal")
    if behavior == "sk":
        keycode = arguments[0] if arguments else ""
        return KeyLabel(fit_label("SK" + keycode_display(keycode)), kind="mod")
    if behavior == "sl":
        keycode = arguments[0] if arguments else ""
        return KeyLabel(fit_label("SL" + keycode_display(keycode)), kind="mod")
    if behavior == "caps_word":
        return KeyLabel("CAPS", kind="mod")
    if behavior == "key_repeat":
        return KeyLabel("RPT", kind="normal")
    if behavior == "soft_off":
        return KeyLabel("OFF", kind="normal")
    if behavior == "studio_unlock":
        return KeyLabel("UNLOCK", kind="normal")

    fallback = behavior.upper()
    if arguments:
        fallback += " " + " ".join(arguments)
    return KeyLabel(fit_label(fallback), kind="normal")


# ---------------------------------------------------------------------------
# Terminal table
# ---------------------------------------------------------------------------


def split_row(row: list[str]) -> tuple[list[str], list[str]]:
    half = len(row) // 2
    return row[:half], row[half:]


def keycap_lines(label: KeyLabel) -> list[str]:
    top = "┌" + "─" * KEY_INNER + "┐"
    bottom = "└" + "─" * KEY_INNER + "┘"
    main = "│" + center_label(label.main) + "│"
    sub = "│" + center_label(label.sub) + "│"
    return [top, main, sub, bottom]


def row_width(key_count: int) -> int:
    if key_count <= 0:
        return 0
    if key_count == 1:
        return KEY_WIDTH
    return key_count * KEY_WIDTH + (key_count - 2) + SPLIT_GAP


def render_row(row: list[str], keymap: Keymap) -> list[str]:
    left, right = split_row(row)
    left_lines = [keycap_lines(format_binding(token, keymap)) for token in left]
    right_lines = [keycap_lines(format_binding(token, keymap)) for token in right]
    lines: list[str] = []
    for line_index in range(4):
        left_text = " ".join(parts[line_index] for parts in left_lines)
        right_text = " ".join(parts[line_index] for parts in right_lines)
        if left_text and right_text:
            lines.append(left_text + " " * SPLIT_GAP + right_text)
        else:
            lines.append(left_text or right_text)
    return lines


def layer_binding(layer: Layer, index: int) -> str:
    bindings = layer.bindings
    return bindings[index] if 0 <= index < len(bindings) else ""


def is_transparent(token: str) -> bool:
    behavior, _ = split_binding(token)
    return behavior in {"trans", "none"}


def resolved_binding(keymap: Keymap, layer: Layer, index: int) -> str:
    """Binding at a position, falling through transparent layers to the base."""
    for candidate in reversed(keymap.layers[: layer.index + 1]):
        token = layer_binding(candidate, index)
        if token and not is_transparent(token):
            return token
    return layer_binding(layer, index)


def press_caption(label: KeyLabel) -> str:
    """The key you physically press: the tap key for tap-hold behaviors."""
    if label.kind in {"mod", "layer"} and label.sub:
        return label.sub
    return label.main or label.sub or "·"


def combo_keys(combo: Combo, layer: Layer, keymap: Keymap) -> str:
    captions = []
    for position in combo.positions:
        token = resolved_binding(keymap, layer, position)
        captions.append(press_caption(format_binding(token, keymap)) if token else "?")
    return " + ".join(captions)


def combo_output(combo: Combo, keymap: Keymap) -> str:
    if not combo.bindings:
        return "·"
    label = format_binding(combo.bindings[0], keymap)
    return label.main + (f" {label.sub}" if label.sub else "")


def print_layer_combos(layer: Layer, keymap: Keymap) -> None:
    """List combos using this layer's key names instead of raw positions."""
    if not keymap.combos:
        return
    rows = [
        (combo.name, combo_keys(combo, layer, keymap), combo_output(combo, keymap))
        for combo in keymap.combos
    ]
    name_width = max(len(name) for name, _, _ in rows)
    key_width = max(display_width(keys) for _, keys, _ in rows)
    print("Combos")
    for name, keys, output in rows:
        padding = " " * (key_width - display_width(keys))
        print(f"  {name:<{name_width}}  {keys}{padding}  → {output}")


def print_layer(layer: Layer, keymap: Keymap, show_combos: bool = True) -> None:
    print(f"{layer.name} ({layer.index})")
    print("─" * (display_width(layer.name) + len(f" ({layer.index})")))
    widths = [row_width(len(row)) for row in layer.rows]
    target = max(widths) if widths else 0
    for row, width in zip(layer.rows, widths):
        indent = " " * max(0, (target - width) // 2)
        for line in render_row(row, keymap):
            print(indent + line)
    if any("+" in format_binding(token, keymap).sub for token in layer.bindings):
        print(f"modifiers: {modifier_legend()}")
    if show_combos and keymap.combos:
        print()
        print_layer_combos(layer, keymap)
    print()


def print_combos(keymap: Keymap, layer: Layer | None = None) -> None:
    print("Combos")
    print("──────")
    reference = layer or (keymap.layers[0] if keymap.layers else None)
    if not keymap.combos or reference is None:
        print("  (none)")
        print()
        return
    rows = []
    for combo in keymap.combos:
        positions = " ".join(str(position) for position in combo.positions)
        keys = combo_keys(combo, reference, keymap)
        rows.append((combo.name, positions, keys, combo_output(combo, keymap)))
    name_width = max(len(row[0]) for row in rows)
    position_width = max(len(row[1]) for row in rows)
    key_width = max(display_width(row[2]) for row in rows)
    for name, positions, keys, output in rows:
        padding = " " * (key_width - display_width(keys))
        print(
            f"  {name:<{name_width}}  {positions:<{position_width}}  "
            f"{keys}{padding}  → {output}"
        )
    print()


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

SVG_KEY_W = 44
SVG_KEY_H = 44
SVG_GAP = 6
SVG_SPLIT_GAP = 24
SVG_MARGIN = 20
SVG_TITLE_H = 40
SVG_LEGEND_H = 28

SVG_COLORS = {
    "normal": ("#ffffff", "#343a40", "#111111"),
    "layer": ("#e7f5ff", "#1971c2", "#0b4f8a"),
    "mod": ("#f3f0ff", "#7048e8", "#4c2db3"),
    "media": ("#fff4e6", "#e8590c", "#a33b00"),
    "mouse": ("#ebfbee", "#2f9e44", "#1b6b2c"),
    "trans": ("#f1f3f5", "#ced4da", "#868e96"),
}

SVG_LEGEND = [
    ("layer", "layer"),
    ("mod", "mod"),
    ("media", "media"),
    ("mouse", "mouse"),
    ("trans", "trans"),
]


def svg_row_width(key_count: int) -> int:
    if key_count <= 0:
        return 0
    if key_count == 1:
        return SVG_KEY_W
    return key_count * SVG_KEY_W + (key_count - 2) * SVG_GAP + SVG_SPLIT_GAP


def svg_keycap(x: float, y: float, label: KeyLabel) -> str:
    fill, stroke, text_color = SVG_COLORS.get(label.kind, SVG_COLORS["normal"])
    parts = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{SVG_KEY_W}" height="{SVG_KEY_H}" '
        f'rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
    ]
    if label.sub:
        parts.append(
            f'<text x="{x + SVG_KEY_W / 2:.1f}" y="{y + 17:.1f}" text-anchor="middle" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
            f'font-size="13" font-weight="600" fill="{text_color}">{escape(label.main)}</text>'
        )
        parts.append(
            f'<text x="{x + SVG_KEY_W / 2:.1f}" y="{y + 34:.1f}" text-anchor="middle" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
            f'font-size="10" fill="{text_color}">{escape(label.sub)}</text>'
        )
    else:
        parts.append(
            f'<text x="{x + SVG_KEY_W / 2:.1f}" y="{y + 27:.1f}" text-anchor="middle" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
            f'font-size="13" font-weight="600" fill="{text_color}">{escape(label.main)}</text>'
        )
    return "".join(parts)


def render_svg(layer: Layer, keymap: Keymap, legend: bool = True) -> str:
    widths = [svg_row_width(len(row)) for row in layer.rows]
    canvas_w = max(widths, default=200) + 2 * SVG_MARGIN
    legend_h = SVG_LEGEND_H if legend else 0
    canvas_h = (
        SVG_MARGIN
        + SVG_TITLE_H
        + len(layer.rows) * (SVG_KEY_H + SVG_GAP)
        - SVG_GAP
        + legend_h
        + SVG_MARGIN
    )
    canvas_h = max(canvas_h, 120)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" role="img">',
        f"<title>{escape(layer.name)} layer</title>",
        f'<rect width="{canvas_w}" height="{canvas_h}" fill="#f8f9fa"/>',
        f'<text x="{SVG_MARGIN}" y="{SVG_MARGIN + 24}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
        f'font-size="20" font-weight="700" fill="#111111">{escape(layer.name)} ({layer.index})</text>',
        f'<text x="{canvas_w - SVG_MARGIN}" y="{SVG_MARGIN + 24}" text-anchor="end" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
        f'font-size="12" fill="#868e96">{escape(layer.node)}</text>',
    ]

    for row_index, row in enumerate(layer.rows):
        row_w = svg_row_width(len(row))
        x = (canvas_w - row_w) / 2
        y = SVG_MARGIN + SVG_TITLE_H + row_index * (SVG_KEY_H + SVG_GAP)
        left, right = split_row(row)

        for token in left:
            parts.append(svg_keycap(x, y, format_binding(token, keymap)))
            x += SVG_KEY_W + SVG_GAP
        if left and right:
            x += SVG_SPLIT_GAP - SVG_GAP
        for token in right:
            parts.append(svg_keycap(x, y, format_binding(token, keymap)))
            x += SVG_KEY_W + SVG_GAP

    if legend:
        legend_y = canvas_h - SVG_MARGIN - 12
        x = SVG_MARGIN
        for kind, label in SVG_LEGEND:
            fill, stroke, _ = SVG_COLORS[kind]
            parts.append(
                f'<rect x="{x}" y="{legend_y - 9}" width="12" height="12" rx="2" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{x + 17}" y="{legend_y + 1}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
                f'font-size="11" fill="#495057">{label}</text>'
            )
            x += 82

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "layer"


def write_svg(
    layer: Layer,
    keymap: Keymap,
    directory: Path,
    legend: bool = True,
    announce: bool = False,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{layer.index:02d}-{slugify(layer.name)}.svg"
    path.write_text(render_svg(layer, keymap, legend=legend), encoding="utf-8")
    if announce:
        print(f"wrote {path}", file=sys.stderr)
    return path


# ---------------------------------------------------------------------------
# fzf and chafa integration
# ---------------------------------------------------------------------------


def run_fzf(layers: list[Layer]) -> list[int] | None:
    if not shutil.which("fzf"):
        return None
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    lines = [f"{layer.index}: {layer.name}" for layer in layers]
    process = subprocess.run(
        ["fzf", "--prompt=layer> ", "--height=40%", "--reverse", "--no-multi"],
        input="\n".join(lines),
        text=True,
        capture_output=True,
    )
    if process.returncode != 0:
        return []
    selected = process.stdout.strip()
    if not selected:
        return []
    try:
        return [int(selected.split(":", 1)[0])]
    except ValueError:
        return []


def render_with_chafa(path: Path) -> bool:
    executable = shutil.which("chafa")
    if not executable:
        print(
            "chafa not found; install chafa or open the SVG directly",
            file=sys.stderr,
        )
        return False
    process = subprocess.run(
        [executable, "--format=symbols", "--size=100x40", str(path)]
    )
    return process.returncode == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview ZMK keymap layers as terminal tables or SVG images.",
    )
    parser.add_argument("layers", nargs="*", help="layer name(s) or index(es)")
    parser.add_argument("--keymap", type=Path, default=DEFAULT_KEYMAP, help="path to keymap")
    parser.add_argument("--all", action="store_true", help="print every layer")
    parser.add_argument("--list", action="store_true", help="list layer names only")
    parser.add_argument("--combos", action="store_true", help="print the combo table")
    parser.add_argument("--no-combos", action="store_true", help="omit combos from layer tables")
    parser.add_argument("--svg", action="store_true", help="write SVG files")
    parser.add_argument("--svg-dir", type=Path, default=DEFAULT_SVG_DIR, help="SVG output directory")
    parser.add_argument("--chafa", action="store_true", help="render SVG with chafa")
    parser.add_argument("--table", action="store_true", help="print the table even with --chafa")
    parser.add_argument("--quiet", action="store_true", help="suppress table and file messages")
    parser.add_argument("--no-picker", action="store_true", help="skip the fzf picker")
    parser.add_argument("--no-legend", action="store_true", help="omit the SVG legend")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    keymap = parse_keymap(args.keymap)

    if args.list:
        for layer in keymap.layers:
            print(f"{layer.index}\t{layer.name}\t{layer.node}")
        return 0

    if args.combos and not args.layers and not args.all and not args.svg:
        print_combos(keymap)
        return 0

    selected: list[Layer] = []
    if args.all:
        selected = keymap.layers
    elif args.layers:
        for argument in args.layers:
            layer = keymap.resolve_layer(argument)
            if layer is None:
                print(f"unknown layer: {argument}", file=sys.stderr)
                return 1
            selected.append(layer)
    elif not args.no_picker:
        picked = run_fzf(keymap.layers)
        if picked is None:
            selected = keymap.layers
        elif not picked:
            return 0
        else:
            selected = [keymap.layers[index] for index in picked]
    else:
        selected = keymap.layers

    show_table = not args.quiet and not (args.chafa and not args.table)

    temp_directory: Path | None = None
    if args.chafa and not args.svg:
        temp_directory = Path(tempfile.mkdtemp(prefix="keymap-preview-"))

    try:
        if args.combos and not show_table:
            print_combos(keymap)

        for layer in selected:
            svg_path: Path | None = None
            if args.svg:
                svg_path = write_svg(
                    layer,
                    keymap,
                    args.svg_dir,
                    legend=not args.no_legend,
                    announce=not args.quiet,
                )
            elif args.chafa:
                assert temp_directory is not None
                svg_path = write_svg(
                    layer,
                    keymap,
                    temp_directory,
                    legend=not args.no_legend,
                    announce=False,
                )

            if show_table:
                print_layer(layer, keymap, show_combos=not args.no_combos)

            if args.chafa:
                assert svg_path is not None
                render_with_chafa(svg_path)
                if len(selected) > 1:
                    print()
    finally:
        if temp_directory is not None:
            shutil.rmtree(temp_directory, ignore_errors=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
