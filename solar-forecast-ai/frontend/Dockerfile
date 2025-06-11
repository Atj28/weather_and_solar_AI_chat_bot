FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all files
COPY . .

# Set environment variable for React
ENV NODE_ENV=production

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Install curl for health check
RUN apk add --no-cache curl

# Copy built files to nginx
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 3000
EXPOSE 3000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 