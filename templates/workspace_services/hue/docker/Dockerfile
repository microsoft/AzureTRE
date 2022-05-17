ARG HUE_TAG=4.10.0
ARG CERTIFICATE_URL=https://www.digicert.com/CACerts/BaltimoreCyberTrustRoot.crt.pem

FROM HUE/HUE:${HUE_TAG}
# need to pass args to stage
ARG CERTIFICATE_URL
RUN wget -O /usr/local/share/ca-certificates/mysql.crt.pem ${CERTIFICATE_URL} && update-ca-certificates
COPY . /

RUN /usr/sbin/adduser -D -g users HUE

ENTRYPOINT ["/bin/bash", "-c",  "./configure_HUE.sh & /usr/bin/entrypoint"]
