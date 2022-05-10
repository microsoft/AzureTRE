# NOTE FOR OCW:
All the config has been setup (so no manual steps are needed). Just do:
- Open this folder (`ui`) in the devcontainer
- `cd ./app`
- `yarn start` 


# TRE UI

This is very much a work in progress.

To run: 
- Open this folder (`ui`) in the devcontainer
- Couple of manual steps (for now):
  - We currently use the Swagger AAD app as it's set up for web logins. Find that app, and add `http://localhost:3000` as a reply URI.
  - Find the API app in Azure, and add `http://localhost:3000` as a CORS reply URI.
  - Change the values in `./app/src/config.json`:
    - `rootClientId` / `rootTenantId` => swagger App
    - `treApiClientId` => API client ID
- `cd ./app`
- `yarn start` 

