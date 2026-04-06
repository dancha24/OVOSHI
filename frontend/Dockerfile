# Прод: статика после vite build (актуальный /login с VK ID). VITE_* подставляются на этапе build.
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG VITE_API_URL=
ARG VITE_VK_ID=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_VK_ID=$VITE_VK_ID

RUN npm run build

FROM nginx:alpine

COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
