# Stage 1: Build static assets
FROM node:20-alpine AS build-stage
WORKDIR /app
ARG VITE_API_GATEWAY
ENV VITE_API_GATEWAY=$VITE_API_GATEWAY
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve static assets with Nginx
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
