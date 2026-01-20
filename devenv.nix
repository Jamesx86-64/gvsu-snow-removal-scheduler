# Devenv template for a Python development environment.
# Devenv is a modern development environment manager using nix.
# Upstream URL: https://devenv.sh

{
  config,
  pkgs,
  ...
}:

{
  packages = with pkgs; [

    # Command runner
    just
  ];

  # Formatters
  treefmt = {
    enable = true;
    config.programs = {

      # Language formatter
      ruff-format.enable = true;

      # Keeps Nix files formatted properly
      nixfmt.enable = true;
      deadnix.enable = true;
      statix.enable = true;
    };
  };

  # Enable Python language support (installs most basic tools)
  languages.python = {
    enable = true;
    venv.enable = true;
    manylinux.enable = true;
    patches.buildEnv.enable = true;
    lsp = {
      enable = true;
      package = pkgs.pyright;
    };

    # Python package, use one or the other
    package = pkgs.python3;
    version = null; # Use version number like "3.14.2" or "3.15" to pin

    # Package managers, only use one
    uv = {
      enable = true;
      sync.enable = true;
    };
    poetry.enable = false;
  };

  git-hooks.hooks = {

    # Security & safety
    ripsecrets.enable = true;
    check-merge-conflicts.enable = true;

    # Code quality
    treefmt.enable = true;
    ruff.enable = true;
    typos.enable = true;
    pyright = {
      enable = true;
      entry = "${pkgs.pyright}/bin/pyright --pythonpath ${config.devenv.state}/venv/bin/python";
    };
    pytest = {
      enable = true;
      pass_filenames = false;
      entry = "${config.devenv.state}/venv/bin/pytest";
    };

    # Editor configuration
    check-added-large-files.enable = true;
    editorconfig-checker.enable = true;
    trim-trailing-whitespace.enable = true;
    end-of-file-fixer.enable = true;
  };
}
