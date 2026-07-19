FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY apps/attribute_extractor/frontend/package.json apps/attribute_extractor/frontend/package-lock.json ./
RUN npm ci

COPY apps/attribute_extractor/frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime

ENV API_UPSTREAM=http://backend:8000/
COPY apps/attribute_extractor/frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
