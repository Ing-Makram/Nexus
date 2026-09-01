# syntax=docker/dockerfile:1
# ==============================================================================
# NEXUS production reverse proxy + static SPA host.
#
# Stage 1 builds the React app to static assets.
# Stage 2 is nginx: it serves those assets and reverse-proxies the API to
# Gunicorn (see infrastructure/docker/nginx.prod.conf).
#
# Build context: the repository root.
# ==============================================================================
FROM node:20-slim AS build

WORKDIR /app

# The SPA talks to the API on the same origin, behind this proxy.
ARG VITE_API_URL=/api/v1
ARG VITE_APP_NAME=NEXUS
ARG VITE_ENVIRONMENT=production
ENV VITE_API_URL=$VITE_API_URL \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_ENVIRONMENT=$VITE_ENVIRONMENT

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS proxy

RUN rm /etc/nginx/conf.d/default.conf
COPY infrastructure/docker/nginx.prod.conf /etc/nginx/conf.d/nexus.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx:alpine already runs `nginx -g 'daemon off;'` as its CMD.
