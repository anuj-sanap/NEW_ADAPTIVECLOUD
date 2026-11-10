# frontend/Dockerfile
# Multi-stage production build for AdaptiveCloud React + TypeScript SPA

# Stage 1: Build the production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Cache package installation
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve production assets via Nginx
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
