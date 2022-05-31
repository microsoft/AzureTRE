# TRE UI

This is very much a work in progress.

To run: 
- Open this folder (`ui`) in the devcontainer
- Couple of manual steps (for now):
  - We currently use the Swagger AAD app as it's set up for web logins. Find that app, and add `http://localhost:3000` as a reply URI.
  - Find the API wep app in the core TRE resource group, and add `http://localhost:3000` as a CORS reply URI.
  - Change the values in `./app/src/config.json`:
    - `rootClientId` / `rootTenantId` => swagger App
    - `treApiClientId` => API client ID
    - `debug` => true or false to show debug info in the UI
- `cd ./app`
- `yarn start` 

