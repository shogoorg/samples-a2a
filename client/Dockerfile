# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ---- Stage 1: Build ----
FROM node:22-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Stage 2: Serve ----
FROM nginx:alpine

# Install envsubst (included in gettext)
RUN apk add --no-cache gettext

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy profile JSON for UCP agent profile
COPY --from=builder /app/profile /usr/share/nginx/html/profile

# Copy nginx config template
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 8080

# envsubst replaces ${BUSINESS_AGENT_URL} at startup, then starts nginx
CMD ["/bin/sh", "-c", "envsubst '${BUSINESS_AGENT_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
