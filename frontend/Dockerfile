# Flatland Frontend — React + Vite built and served by nginx
# Build: docker build -t flatland-frontend .
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

FROM nginx:alpine
# Replace default site
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
