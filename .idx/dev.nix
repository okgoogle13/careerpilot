let
 pkgs = import <nixpkgs> {};
in
 {
 flake = {
 devcontainer = {
      # Workspace lifecycle hooks
          workspace = {
            # Runs when a workspace is first created
            onCreate = {
              npm-install = "npm ci --no-audit --prefer-offline --no-progress --timing";
              default.openFiles = [ "README.md" "index.ts" ];
            };
            # Runs when the workspace is (re)started
            onStart = {
              run-server = "if [ -z \"\${AIzaSyBiS3EMRKcddSfGvBZr7MG3Or1tWQdNdlI}\" ]; then \\
 echo 'No Gemini API key detected, enter a Gemini API key from https://aistudio.google.com/app/apikey:' && \\
                read -s GOOGLE_GENAI_API_KEY && \\
                echo 'You can also add to .idx/dev.nix to automatically add to your workspace'
                export GOOGLE_GENAI_API_KEY; \\
                fi && \\
                npm run genkit:dev";
            };
          };
        };
        environment.variables = {
          GOOGLE_GENAI_API_KEY = "AIzaSyBiS3EMRKcddSfGvBZr7MG3Or1tWQdNdlI";
        };
      };
      packages = [ 
 pkgs.flutter
      ];
    };
  };
}
