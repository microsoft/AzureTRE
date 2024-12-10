set -o errexit
set -o pipefail

export LETSENCRYPT_DROP_ALL_RULES=1

make bootstrap mgmt-deploy auth images \
     deploy-core build-and-deploy-ui letsencrypt \
     firewall-install db-migrate show-core-output



echo "Now Running ./only-the-good-bits.sh .... "
./only-the-good-bits.sh
echo "only-the-good-bits.sh is done Now running Make bundle publish register all.... "

make bundle-publish-register-all

echo "Hurrayyyyyyyyyy----- All done"