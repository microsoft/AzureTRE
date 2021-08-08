FROM gitea/gitea:latest
RUN wget -O /usr/local/share/ca-certificates/mysql.crt.pem https://www.digicert.com/CACerts/BaltimoreCyberTrustRoot.crt.pem && update-ca-certificates
ENTRYPOINT ["/bin/bash", "-c", "sleep 120 && gitea admin user create --admin --access-token --username=${GITEA_USERNAME} --password=${GITEA_PASSWD} --email=${GITEA_EMAIL} --must-change-password=false & /usr/bin/entrypoint"]