FROM node:22-alpine
WORKDIR /app
COPY package.json server.mjs auth.mjs ./
COPY data ./data
COPY public ./public
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.mjs"]
