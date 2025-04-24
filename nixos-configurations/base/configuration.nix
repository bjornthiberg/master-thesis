{
  config,
  pkgs,
  lib,
  modulesPath,
  ...
}:

{
  imports = [
    (modulesPath + "/installer/cd-dvd/iso-image.nix") # turns config into ISO
    (modulesPath + "/installer/cd-dvd/channel.nix") # to allow offline build
    (modulesPath + "/profiles/base.nix") # base utilities, filesystem support
  ];

  boot.kernelParams = [ "copytoram" ];
  isoImage.makeEfiBootable = true;
  isoImage.makeUsbBootable = true;
  isoImage.squashfsCompression = "gzip -Xcompression-level 1"; # faster build

  # some stuff from installation-cd-base.nix
  hardware.enableAllHardware = true;
  boot.loader.grub.memtest86.enable = true;
  swapDevices = lib.mkImageMediaOverride [ ];
  fileSystems = lib.mkImageMediaOverride config.lib.isoFileSystems;

  # localization
  time.timeZone = "Europe/Stockholm";
  i18n.defaultLocale = "en_US.UTF-8";
  console.keyMap = "sv-latin1";

  # User account with no password
  users.users.dev = {
    isNormalUser = true;
    extraGroups = [
      "wheel"
      "networkmanager"
    ];
    initialPassword = "";
  };

  # Enable sudo without password
  security.sudo.wheelNeedsPassword = false;

  nixpkgs.config.allowUnfree = true; # allow unfree packages

  environment.systemPackages = with pkgs; [
    rsync
    python3
    coreutils
    home-manager
    git
    vim
    vscode
    gcc
    gnumake
    cmake
    wget
    curl
  ];

  # Enable services
  services.xserver = {
    enable = true;
    displayManager.gdm.enable = true;
    desktopManager.gnome.enable = true;
  };

  # exclude some GNOME software

  environment.gnome.excludePackages = (
    with pkgs;
    [
      atomix
      cheese
      epiphany
      evince
      geary
      gedit
      gnome-characters
      gnome-music
      gnome-photos
      gnome-tour
      hitori
      iagno
      tali
      totem
    ]
  );

  environment.etc."capture-state.py" = {
    source = ./capture-state.py;
  };

  system.stateVersion = "25.05";
}
