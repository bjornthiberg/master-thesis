{
  description = "ramNix Home Manger Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/1e5b653dff12029333a6546c11e108ede13052eb";
    home-manager = {
      url = "github:nix-community/home-manager/5ee44bc7c2e853f144390a12ebe5174ad7e3b9e0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };


  outputs = { nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      homeConfigurations."dev" = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        modules = [ ./home.nix ];
      };
    };
}