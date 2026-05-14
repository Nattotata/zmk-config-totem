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

