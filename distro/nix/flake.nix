{
  description = "Free My ID: asks data brokers to delete a person's listings";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
      # The version comes from the project's own pyproject.toml.
      project = (builtins.fromTOML (builtins.readFile ../../pyproject.toml)).project;
    in
    {
      packages = forAllSystems (pkgs: rec {
        freemyid = pkgs.python3Packages.buildPythonApplication {
          pname = project.name;
          inherit (project) version;
          pyproject = true;

          # Local source tree (the repository root, two levels up).
          src = ../..;

          build-system = [ pkgs.python3Packages.hatchling ];

          dependencies = with pkgs.python3Packages; [
            pydantic
            pyyaml
            typer
            rich
            jinja2
            keyring
            cryptography
            rapidfuzz
            playwright
            fastapi
            uvicorn
            python-multipart
            httpx
            platformdirs
            desktop-notifier
            jsonschema
          ];

          # nixpkgs may lag the minimum versions in pyproject.toml.
          pythonRelaxDeps = true;

          pythonImportsCheck = [ "freemyid" ];

          # Tests need fixtures and a prepared site build; run them in the repo instead.
          doCheck = false;

          meta = {
            description = project.description;
            homepage = project.urls.Homepage;
            license = pkgs.lib.licenses.agpl3Plus;
            mainProgram = "freemyid";
          };
        };
        default = freemyid;
      });

      apps = forAllSystems (pkgs: {
        default = {
          type = "app";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.freemyid}/bin/freemyid";
        };
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          inputsFrom = [ self.packages.${pkgs.stdenv.hostPlatform.system}.freemyid ];
          packages = [
            pkgs.python3Packages.pytest
            pkgs.ruff
          ];
        };
      });
    };
}
