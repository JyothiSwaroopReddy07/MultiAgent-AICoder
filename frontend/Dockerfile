# edited by Kunwarjeet

# Use Node.js 18 alpine image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy project files
COPY . .

# Expose port
EXPOSE 3000

# Set environment variable to ensure React dev server listens on all interfaces
ENV HOST=0.0.0.0

# Command to run the application
CMD ["npm", "start"]

