# TRE UI

Please see the docs for a full overview and deployment instructions.

The UI was built using Create React App and Microsoft Fluent UI. Further details on this in the ./app/README.

## Run the UI
- Ensure `DEPLOY_UI=false` is not set in your `./templates/core/.env` file
- In the root of the repo, run `make tre-deploy`. This will provision the necessary resources in Azure, build and deploy the UI to Azure blob storage, behind the App Gateway used for the API. The deployment process will also create the necessary `config.json`, using the `config.source.json` as a template.
- In Azure AD, locate the TRE Client Apps app (possibly called Swagger App). In the Authentication section add reply URIs for:
  - `http://localhost:3000` (if wanting to run locally)
  - Your deployed App Url - `https://{TRE_ID}.{LOCATION}.cloudapp.azure.com`.

At this point you should be able to navigate to the web app in Azure, log in, and see your workspaces.

### To run locally
- `cd ./ui/app`
- `yarn start`

After making changes to the code, redeploy to Azure by running `make build-and-deploy-ui` in the root of the dev container.
