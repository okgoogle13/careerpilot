{ pkgs, ... }: {
  # The Nix channel to use.
  channel = "stable-23.11";

  # A list of packages to make available in your environment.
  packages = [
    pkgs.nodejs_20
    pkgs.flutter
    pkgs.python311
    pkgs.python311Packages.pip
  ];

  # Environment variables that will be available in the workspace.
  env = {
    # TODO: Move this to a secure secret manager (like Google Secret Manager or a similar service)
    # and load it as an environment variable instead of hardcoding it.
    GOOGLE_GENAI_API_KEY = "AIzaSyBiS3EMRKcddSfGvBZr7MG3Or1tWQdNdlI";
  };

  # IDX-specific configurations
  idx = {
    # Enable workspace previews for web applications
    previews = {
      enable = true;
      previews = {
        web = {
          command = ["npm" "run" "genkit:dev"];
          manager = "web";
        };
      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Commands to run when the workspace is created
      onCreate = {
        install-deps = "npm ci --no-audit --prefer-offline --no-progress --timing";
      };
      # Commands to run when the workspace starts
      onStart = {
        start-dev = "npm run genkit:dev";
      };
    };
  };
}
