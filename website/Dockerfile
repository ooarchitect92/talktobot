FROM node:26-alpine@sha256:ef24c5053d50fdc3e4e56eb4e7ddb7861874ab0fdc797046ba897581deb8e868 AS build
WORKDIR /site
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_APP_URL=http://localhost:3100
ARG VITE_SITE_URL=http://localhost:3300
ENV VITE_APP_URL=$VITE_APP_URL VITE_SITE_URL=$VITE_SITE_URL
RUN npm run build

FROM node:26-alpine@sha256:ef24c5053d50fdc3e4e56eb4e7ddb7861874ab0fdc797046ba897581deb8e868
WORKDIR /site
RUN apk upgrade --no-cache \
    && rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
COPY --from=build /site/dist ./dist
COPY server.mjs ./server.mjs
COPY proxy-context.mjs ./proxy-context.mjs
ENV NODE_ENV=production PORT=8080 API_ORIGIN=http://api:8000
USER node
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s CMD node -e "fetch('http://127.0.0.1:8080/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "server.mjs"]
