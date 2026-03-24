
# refusing to overwrite existing file '/home/xof/Documents/repos/zmk-config-totem/config/west.yml'
#  please merge it manually with '/nix/store/q6s4b751fjp514svn9isij5c83mlpxf4-source/template/config/west.yml'
# wrote: "/home/xof/Documents/repos/zmk-config-totem/config"
#
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    zmk-nix = {
      url = "github:lilyinstarlight/zmk-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, zmk-nix }: let
    forAllSystems = nixpkgs.lib.genAttrs (nixpkgs.lib.attrNames zmk-nix.packages);
  in {
    packages = forAllSystems (system: rec {
      default = firmware;

      firmware = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
        name = "firmware";
        # src = nixpkgs.lib.sourceFilesBySuffices self [ ".board" ".cmake" ".conf" ".defconfig" ".dts" ".dtsi" ".json" ".keymap" ".overlay" ".shield" ".yml" "_defconfig" ];
        board = "seeed_xiao_ble";
        shield = "totem_%PART%";
       src = ./.;
        zephyrDepsHash = "sha256-mUJpGWlU+rGbcWtKs/SuombCJ3RcIDMTiuMicwLX1D4=";
        extraCmakeFlags = [ 
          "-DSHIELD_ROOT=${./.}/config" 
          "-DZMK_CONFIG=${./.}/config"
          "-DBOARD_ROOT=/build/source/zmk/app"
        ];
        meta = {
          description = "ZMK firmware";
          license = nixpkgs.lib.licenses.mit;
          platforms = nixpkgs.lib.platforms.all;
        };
      };

      flash = zmk-nix.packages.${system}.flash.override { inherit firmware; };
      update = zmk-nix.packages.${system}.update;
    });

    devShells = forAllSystems (system: {
      default = zmk-nix.devShells.${system}.default;
    });
  };
}
