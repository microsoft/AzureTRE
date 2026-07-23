ARG GITEA_TAG=1.15
ARG GITEA_BASE_IMAGE_REPO=gitea/gitea
ARG CERTIFICATE_URL=https://www.digicert.com/CACerts/BaltimoreCyberTrustRoot.crt.pem

FROM ${GITEA_BASE_IMAGE_REPO}:${GITEA_TAG}
# need to pass args to stage
ARG CERTIFICATE_URL
RUN wget -nv -O /usr/local/share/ca-certificates/mysql.crt.pem ${CERTIFICATE_URL} && update-ca-certificates
ENTRYPOINT ["/bin/bash", "-c", "sleep 120 && gitea admin user create --admin --access-token --username=${GITEA_USERNAME} --password=${GITEA_PASSWD} --email=${GITEA_EMAIL} --must-change-password=false & /usr/bin/entrypoint"]
