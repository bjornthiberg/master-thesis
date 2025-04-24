{
  config,
  pkgs,
  lib,
  ...
}:

{
  nixpkgs.config.allowUnfree = true;

  home.username = "dev";
  home.homeDirectory = "/home/dev";

  home.stateVersion = "25.05";

  # Let Home Manager install and manage itself.
  programs.home-manager.enable = true;

  # shell configuration
  programs.bash = {
    enable = true;
    shellAliases = {
      ll = "ls -la";
      update = "sudo nixos-rebuild switch";
      ga = "git add";
      gc = "git commit";
      gp = "git push";
      gs = "git status";
    };
    bashrcExtra = ''
      export PS1="\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\> "
    '';
    initExtra = ''
      export HISTSIZE=10000
      export HISTFILESIZE=10000
    '';
  };

  # vscode
  programs.vscode = {
    enable = true;
    extensions = [
      pkgs.vscode-extensions.mhutchie.git-graph
    ];

    userSettings = {
      "editor.minimap.enabled" = false;
      "telemetry.telemetryLevel" = "off";
    };

    keybindings = [
      {
        key = "alt+1";
        command = "workbench.action.focusFirstEditorGroup";
      }
      {
        key = "ctrl+1";
        command = "workbench.action.openEditorAtIndex1";
      }
    ];
  };

  # Git
  programs.git = {
    enable = true;
    userName = "Developer";
    userEmail = "dev@example.com";
    extraConfig = {
      init.defaultBranch = "main";
    };
  };

  # GNOME dconf settings
  dconf.settings = {
    "org/gnome/desktop/interface" = {
      color-scheme = "prefer-dark";
      enable-hot-corners = true;
      font-antialiasing = "rgba";
      font-hinting = "slight";
      clock-show-weekday = true;
      clock-show-date = true;
    };

    "org/gnome/desktop/wm/preferences" = {
      button-layout = "appmenu:minimize,maximize,close";
      focus-mode = "click";
      num-workspaces = 4;
    };

    "org/gnome/desktop/peripherals/mouse" = {
      natural-scroll = false;
      speed = 0.3;
    };

    "org/gnome/settings-daemon/plugins/power" = {
      sleep-inactive-ac-type = "nothing";
      power-button-action = "interactive";
    };

    "org/gnome/desktop/input-sources" = {
      sources = [
        (lib.hm.gvariant.mkTuple [
          "xkb"
          "se"
        ])
      ];
    };
  };

  home.sessionVariables = {
    EDITOR = "nano";
    VISUAL = "code";
    PATH = "$HOME/.local/bin:$PATH";
    LANG = "en_US.UTF-8";
    LC_ALL = "en_US.UTF-8";
    TERM = "xterm-256color";
  };
}
