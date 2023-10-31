FROM python:3.7-slim

RUN set -ex \
    ; apt-get update \
    ; apt-get install -y \
        supervisor \
        curl \
        nginx \
        nano \
    # remove apt cache
    ; rm -rf /var/lib/apt/lists/* \
    # remove default nginx configs
    ; rm -rf /etc/nginx/conf.d/* \
    # set root as nginx user
    ; sed -i 's/^user.*/user root;/' /etc/nginx/nginx.conf

WORKDIR /app

COPY . .

RUN pip3 install -r requirements.txt --no-cache-dir

COPY ./devops/nginx.conf /etc/nginx/conf.d/
COPY ./devops/supervisord.conf /etc/supervisor/

ENTRYPOINT  ["supervisord"]
