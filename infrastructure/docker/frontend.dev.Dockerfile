FROM node:20-slim

# Set work directory
WORKDIR /app

# Install dependencies from the committed lockfile for reproducible builds
COPY frontend/package.json frontend/package-lock.json /app/
RUN npm ci

# Copy project
COPY frontend /app/

# Expose port
EXPOSE 5173

# Command to run on container start
# We use --host to allow external connections (from host or other containers)
CMD ["npm", "run", "dev", "--", "--host"]
