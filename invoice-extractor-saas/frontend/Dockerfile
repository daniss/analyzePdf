FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application (skip for development)
# RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "run", "dev"]