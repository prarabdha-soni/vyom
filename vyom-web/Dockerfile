# syntax=docker/dockerfile:1
# The Vyom console (and marketing pages) as a self-contained Node server.
# Runtime env: VYOM_OS_URL, VYOM_SESSION_SECRET, VYOM_SAMPLE_WORKSPACE (on|off).
# Pin node:22-alpine by digest in CI.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS build
WORKDIR /app
# Public values are inlined at build time; never pass a secret here.
ARG NEXT_PUBLIC_SITE_URL=""
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_ROOT_DOMAIN=""
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_OUTPUT=standalone \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_ROOT_DOMAIN=$NEXT_PUBLIC_ROOT_DOMAIN
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -S -g 10001 vyom && adduser -S -D -H -u 10001 -G vyom vyom
COPY --from=build --chown=10001:10001 /app/.next/standalone ./
COPY --from=build --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=build --chown=10001:10001 /app/public ./public
USER 10001:10001
EXPOSE 3000
CMD ["node", "server.js"]
