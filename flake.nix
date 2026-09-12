{
  description = "CCraft nix shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs =
    { nixpkgs, flake-utils, ... }:

    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            gum
            just
            mdbook
            just-lsp
            uv
          ];

          shellHook = ''
            {
              gum style --bold --foreground 214 "A CODE CRAFTER shapes software by hand :)"
            } | gum style --border rounded --border-foreground 214 --padding "0 2" --margin "1 0"
          '';
        };
      }
    );
}
