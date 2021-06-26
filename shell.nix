with import <nixpkgs> {};
mkShell {
    buildInputs = [
        (python38.withPackages (ps: with ps; [
            flake8
            pandas
            requests
        ]))
        shellcheck
    ];
    shellHook = ''
        . .shellhook
    '';
}
