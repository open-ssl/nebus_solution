# syntax=docker/dockerfile:1

# Static UI for exercising the payments API, served by nginx and reverse-proxying
# /api to the api service (same-origin, so the browser needs no CORS).
FROM nginx:alpine

COPY services/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY services/frontend/static /usr/share/nginx/html

EXPOSE 80
