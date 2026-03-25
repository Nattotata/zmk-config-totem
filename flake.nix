
# refusing to overwrite existing file '/home/xof/Documents/repos/zmk-config-totem/config/west.yml'
#  please merge it manually with '/nix/store/q6s4b751fjp514svn9isij5c83mlpxf4-source/template/config/west.yml'
# wrote: "/home/xof/Documents/repos/zmk-config-totem/config"
#
# {
#   inputs = {
#     nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
#
#     zmk-nix = {
#       url = "github:lilyinstarlight/zmk-nix";
#       inputs.nixpkgs.follows = "nixpkgs";
#     };
#   };
#
#   outputs = { self, nixpkgs, zmk-nix }: let
#     forAllSystems = nixpkgs.lib.genAttrs (nixpkgs.lib.attrNames zmk-nix.packages);
#   in {
#     packages = forAllSystems (system: rec {
#       default = firmware;
#
#       firmware = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
#         name = "firmware";
#         # src = nixpkgs.lib.sourceFilesBySuffices self [ ".board" ".cmake" ".conf" ".defconfig" ".dts" ".dtsi" ".json" ".keymap" ".overlay" ".shield" ".yml" "_defconfig" ];
#         board = "seeeduino_xiao_ble";
#         shield = "totem_%PART%";
#        src = ./.;
#         zephyrDepsHash = "sha256-mUJpGWlU+rGbcWtKs/SuombCJ3RcIDMTiuMicwLX1D4=";
#         extraCmakeFlags = [ 
#           "-DSHIELD_ROOT=${./.}/config/boards/shields/totem" 
#           "-DZMK_CONFIG=${./.}/config"
#           "-DBOARD_ROOT=${./.}/zmk/app"
#         ];
#         # meta = {
#         #   description = "ZMK firmware";
#         #   license = nixpkgs.lib.licenses.mit;
#         #   platforms = nixpkgs.lib.platforms.all;
#         # };
#       };
#
#       flash = zmk-nix.packages.${system}.flash.override { inherit firmware; };
#       update = zmk-nix.packages.${system}.update;
#     });
#
#     devShells = forAllSystems (system: {
#       default = zmk-nix.devShells.${system}.default;
#     });
#   };
# }
#

{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    zmk-nix = {
      url = "github:lilyinstarlight/zmk-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, zmk-nix }:
    let
      system = "x86_64-linux"; # Adjust to "aarch64-linux" or "x86_64-darwin" if needed
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      packages.${system}.default = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
        name = "totem-firmware";
        src = ./.;
        
        # Use the name that worked in your previous commit
        board = "seeeduino_xiao_ble"; 
        shield = "totem_%PART%";

        # This hash MUST match the content of your west.yml. 
        # If you changed west.yml, Nix will give you the new hash in the error.
        # zephyrDepsHash = "sha256-mUJpGWlU+rGbcWtKs/SuombCJ3RcIDMTiuMicwLX1D4=";
        zephyrDepsHash = "sha256-DOz+hpthxe7jyzZouYpe/aFy9RQgTFnIp+HUMmz3v50=";
        extraCmakeFlags = [
          "-DZMK_CONFIG=${./.}/config"
          "-DSHIELD_ROOT=${./.}/config"
        ];
      };
    };
}
