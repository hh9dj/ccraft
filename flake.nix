{
  description = "CCraft nix shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      devShellsFor =
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              gum
              just
              mdbook
              just-lsp
            ];
            shellHook = ''
              {
                gum style --bold --foreground 214 "A CODE CRAFTER shapes software by hand :)"
              } | gum style --border rounded --border-foreground 214 --padding "0 2" --margin "1 0"
            '';
          };

          # alternative shell profile : nix develop .#special
          special = pkgs.mkShell { };
        };
    in
    {
      devShells = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-darwin" ] devShellsFor;
    };
}
