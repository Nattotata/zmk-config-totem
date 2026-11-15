<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/docs/images/TOTEM_logo_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="/docs/images/TOTEM_logo_bright.svg">
  <img alt="TOTEM logo font" src="/docs/images/TOTEM_logo_bright.svg">
</picture>

# ZMK CONFIG FOR THE TOTEM SPLIT KEYBOARD

[Here](https://github.com/GEIGEIGEIST/totem) you can find the hardware files and build guide.\
[Here](https://github.com/GEIGEIGEIST/qmk-config-totem) you can find the QMK config for the TOTEM.

TOTEM is a 38 key column-staggered split keyboard running [ZMK](https://zmk.dev/) or [QMK](https://docs.qmk.fm/). It's meant to be used with a SEEED XIAO BLE or RP2040.

![TOTEM layout](/docs/images/TOTEM_layout.svg)

## KEYMAP PREVIEW

`tools/keymap.py` reads `config/totem.keymap` and prints Unicode keycap tables in
the terminal. It needs Python 3.10+ and no third-party packages.

```sh
just keymap                 # fzf picker, or all layers when output is piped
just keymap BASE            # print one layer
just keymap-all             # print every layer
just keymap-list            # list layer names and indices
just keymap-combos          # print the combo table
just keymap-svg             # write one SVG per layer to docs/images/layers
just keymap-image           # render a layer with chafa (fzf picker)
```

The raw command is also available:

```sh
python3 tools/keymap.py --all
python3 tools/keymap.py BASE --svg
python3 tools/keymap.py NAVI --chafa
python3 tools/keymap.py --combos
```

`fzf` and `chafa` are optional. Without `fzf`, the script prints all layers.
Without `chafa`, use `--svg` to write images you can open in a browser.

Modifiers print as words (`ctrl`, `alt`, `shift`, `meta`); `meta` is the
GUI/Super/Cmd key. When a key stacks two modifiers, they collapse to their
first letters (`S`, `C`, `A`, `M`) and a legend is printed under that layer.

Each layer also lists its combos using that layer's key names instead of raw
`key-positions` numbers, so you can see which keys to press. Transparent keys
fall through to the layer below. Pass `--no-combos` to hide the combo list.

## HOW TO USE

- fork this repo
- `git clone` your repo, to create a local copy on your PC (you can use the [command line](https://www.atlassian.com/git/tutorials) or [github desktop](https://desktop.github.com/))
- adjust the totem.keymap file (find all the keycodes on [the zmk docs pages](https://zmk.dev/docs/codes/))
- `git push` your repo to your fork
- on the GitHub page of your fork navigate to "Actions"
- scroll down and unzip the `firmware.zip` archive that contains the latest firmware
- connect the left half of the TOTEM to your PC, press reset twice
- the keyboard should now appear as a mass storage device
- drag'n'drop the `totem_left-seeeduino_xiao_ble-zmk.uf2` file from the archive onto the storage device
- repeat this process with the right half and the `totem_right-seeeduino_xiao_ble-zmk.uf2` file.

Edit here: <https://nickcoutsos.github.io/keymap-editor/>
