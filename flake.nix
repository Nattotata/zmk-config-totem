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
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      packages.${system}.default = zmk-nix.legacyPackages.${system}.buildSplitKeyboard {
        name = "totem-firmware";
        src = ./.;
        board = "seeeduino_xiao_ble"; 
        shield = "totem_%PART%";
        zephyrDepsHash = "sha256-DOz+hpthxe7jyzZouYpe/aFy9RQgTFnIp+HUMmz3v50=";
        extraCmakeFlags = [
          "-DZMK_CONFIG=${./.}/config"
          "-DSHIELD_ROOT=${./.}/config"
        ];
      };
    };
}
