# Generate the client using openapi-generator

```bash
cd cli
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
    -i https://ocwtre32.northeurope.cloudapp.azure.com/api/openapi.json \
    -g python \
    -o /local/client
```