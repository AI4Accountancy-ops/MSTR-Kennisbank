# ---- Stage 1: Build the React app ----
FROM node:20 AS build

WORKDIR /app

# Copy package and lock files for dependency installation
COPY package*.json ./

RUN npm install

# Environment argument with a default of development
ARG ENVIRONMENT=dev

# Copy environment files using wildcard
COPY env* ./
RUN cp "env (frontend dev)" .env

# Copy the rest of the frontend code
COPY . .
ARG API_URL=/api

# Set environment variables for the build
ENV VITE_ENVIRONMENT=${ENVIRONMENT}
ENV VITE_API_URL=${API_URL}

# Build the production-ready static files
RUN npm run build

# ---- Stage 2: Serve with NGINX ----
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Create a runtime config that checks for environment variable, defaulting to /api
RUN echo 'window.RUNTIME_CONFIG = { apiUrl: "/api" };' > /usr/share/nginx/html/runtime-config.js

EXPOSE 80

# Use CMD only, no ENTRYPOINT
CMD ["nginx", "-g", "daemon off;"]
