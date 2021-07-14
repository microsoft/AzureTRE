 docker build -f ./vm_porter/Dockerfile -t rp .

 docker run -it -v /var/run/docker.sock:/var/run/docker.sock  --env-file .env  rp