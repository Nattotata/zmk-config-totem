# list available commands
default:
    just -l

# the result is a symlink to nix store
# this creates a local copy for convenience
copy_result:
    cp -rL ./result ./token_firmware
    chmod -R +w ./token_firmware

# build the firmware
build:
    nix build

# preview one layer in the terminal (fzf picker when no layer is given)
keymap *LAYER:
    python3 tools/keymap.py {{LAYER}}

# preview every layer
keymap-all:
    python3 tools/keymap.py --all

# list layer names and indices
keymap-list:
    python3 tools/keymap.py --list

# print the combo table
keymap-combos:
    python3 tools/keymap.py --combos

# write one SVG per layer to docs/images/layers
keymap-svg:
    python3 tools/keymap.py --all --svg --quiet

# render a layer with chafa (fzf picker when no layer is given)
keymap-image *LAYER:
    python3 tools/keymap.py {{LAYER}} --chafa
