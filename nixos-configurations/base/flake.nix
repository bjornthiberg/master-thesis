{
  description = "ramnix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/1e5b653dff12029333a6546c11e108ede13052eb";
    home-manager = {
      url = "github:nix-community/home-manager/5ee44bc7c2e853f144390a12ebe5174ad7e3b9e0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      home-manager,
      ...
    }:
    {
      nixosConfigurations.ramnix = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./configuration.nix
          home-manager.nixosModules.home-manager
          {
            home-manager.useGlobalPkgs = true;
            home-manager.useUserPackages = true;
            # No home.nix in baseline
          }
        ];
      };

      packages.x86_64-linux.default = self.nixosConfigurations.ramnix.config.system.build.isoImage;
    };
}
