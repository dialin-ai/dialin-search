FROM node:20-alpine AS base

LABEL com.onyx.maintainer="founders@onyx.app"
LABEL com.onyx.description="This image is the web/frontend container of Onyx which \
contains code for both the Community and Enterprise editions of Onyx. If you do not \
have a contract or agreement with DanswerAI, you are not permitted to use the Enterprise \
Edition features outside of personal development or testing purposes. Please reach out to \
founders@onyx.app for more information. Please visit https://github.com/onyx-dot-app/onyx"

# Default ONYX_VERSION, typically overriden during builds by GitHub Actions.
ARG ONYX_VERSION=0.0.0-dev
ENV ONYX_VERSION=${ONYX_VERSION}
RUN echo "ONYX_VERSION: ${ONYX_VERSION}"

# Step 1. Install dependencies + rebuild the source code only when needed
FROM base AS builder
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Add NODE_OPTIONS argument
ARG NODE_OPTIONS="--max-old-space-size=8192"
ENV NODE_OPTIONS=${NODE_OPTIONS}

# Copy package files first to leverage Docker cache
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the source code
COPY . .

# needed to get the `standalone` dir we expect later
ENV NEXT_PRIVATE_STANDALONE=true

# Disable automatic telemetry collection
ENV NEXT_TELEMETRY_DISABLED=1

# Combine all environment variables into a single layer
ENV NEXT_PUBLIC_DISABLE_STREAMING=${NEXT_PUBLIC_DISABLE_STREAMING} \
    NEXT_PUBLIC_NEW_CHAT_DIRECTS_TO_SAME_PERSONA=${NEXT_PUBLIC_NEW_CHAT_DIRECTS_TO_SAME_PERSONA} \
    NEXT_PUBLIC_POSITIVE_PREDEFINED_FEEDBACK_OPTIONS=${NEXT_PUBLIC_POSITIVE_PREDEFINED_FEEDBACK_OPTIONS} \
    NEXT_PUBLIC_NEGATIVE_PREDEFINED_FEEDBACK_OPTIONS=${NEXT_PUBLIC_NEGATIVE_PREDEFINED_FEEDBACK_OPTIONS} \
    NEXT_PUBLIC_DEFAULT_SIDEBAR_OPEN=${NEXT_PUBLIC_DEFAULT_SIDEBAR_OPEN} \
    NEXT_PUBLIC_THEME=${NEXT_PUBLIC_THEME} \
    NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=${NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED} \
    NEXT_PUBLIC_DISABLE_LOGOUT=${NEXT_PUBLIC_DISABLE_LOGOUT} \
    NEXT_PUBLIC_CUSTOM_REFRESH_URL=${NEXT_PUBLIC_CUSTOM_REFRESH_URL} \
    NEXT_PUBLIC_POSTHOG_KEY=${NEXT_PUBLIC_POSTHOG_KEY} \
    NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST} \
    NEXT_PUBLIC_CLOUD_ENABLED=${NEXT_PUBLIC_CLOUD_ENABLED} \
    NEXT_PUBLIC_SENTRY_DSN=${NEXT_PUBLIC_SENTRY_DSN} \
    NEXT_PUBLIC_GTM_ENABLED=${NEXT_PUBLIC_GTM_ENABLED} \
    NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED=${NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED} \
    NEXT_PUBLIC_INCLUDE_ERROR_POPUP_SUPPORT_LINK=${NEXT_PUBLIC_INCLUDE_ERROR_POPUP_SUPPORT_LINK} \
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}

# Use NODE_OPTIONS in the build command
RUN NODE_OPTIONS="${NODE_OPTIONS}" npx next build

# Step 2. Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

# Remove global node modules and create user in a single layer
RUN rm -rf /usr/local/lib/node_modules && \
    addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

USER nextjs

# Copy all necessary files in a single layer
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Set all environment variables in a single layer
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_DISABLE_STREAMING=${NEXT_PUBLIC_DISABLE_STREAMING} \
    NEXT_PUBLIC_NEW_CHAT_DIRECTS_TO_SAME_PERSONA=${NEXT_PUBLIC_NEW_CHAT_DIRECTS_TO_SAME_PERSONA} \
    NEXT_PUBLIC_POSITIVE_PREDEFINED_FEEDBACK_OPTIONS=${NEXT_PUBLIC_POSITIVE_PREDEFINED_FEEDBACK_OPTIONS} \
    NEXT_PUBLIC_NEGATIVE_PREDEFINED_FEEDBACK_OPTIONS=${NEXT_PUBLIC_NEGATIVE_PREDEFINED_FEEDBACK_OPTIONS} \
    NEXT_PUBLIC_THEME=${NEXT_PUBLIC_THEME} \
    NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=${NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED} \
    NEXT_PUBLIC_DEFAULT_SIDEBAR_OPEN=${NEXT_PUBLIC_DEFAULT_SIDEBAR_OPEN} \
    NEXT_PUBLIC_DISABLE_LOGOUT=${NEXT_PUBLIC_DISABLE_LOGOUT} \
    NEXT_PUBLIC_CUSTOM_REFRESH_URL=${NEXT_PUBLIC_CUSTOM_REFRESH_URL} \
    NEXT_PUBLIC_POSTHOG_KEY=${NEXT_PUBLIC_POSTHOG_KEY} \
    NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST} \
    NEXT_PUBLIC_CLOUD_ENABLED=${NEXT_PUBLIC_CLOUD_ENABLED} \
    NEXT_PUBLIC_SENTRY_DSN=${NEXT_PUBLIC_SENTRY_DSN} \
    NEXT_PUBLIC_GTM_ENABLED=${NEXT_PUBLIC_GTM_ENABLED} \
    NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED=${NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED} \
    NEXT_PUBLIC_INCLUDE_ERROR_POPUP_SUPPORT_LINK=${NEXT_PUBLIC_INCLUDE_ERROR_POPUP_SUPPORT_LINK} \
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}

CMD ["node", "server.js"]
