# Stage 1: Build the Angular application
FROM node:22 AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build --prod

# Stage 2: Serve the application from a lightweight web server
FROM nginx:alpine

COPY --from=build /app/dist/flask-angular-app/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

