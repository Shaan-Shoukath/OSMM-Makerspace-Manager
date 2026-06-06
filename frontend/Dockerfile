FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_URL=/api
ARG VITE_HMAC_CLIENT_ID=
ARG VITE_HMAC_SECRET=

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_HMAC_CLIENT_ID=$VITE_HMAC_CLIENT_ID
ENV VITE_HMAC_SECRET=$VITE_HMAC_SECRET

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
