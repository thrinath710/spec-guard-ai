import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";

const nextConfig: NextConfig = {
  /* config options here */
};

// NEXT_PUBLIC_* values are inlined at build time, so a hosted build that is missing
// NEXT_PUBLIC_API_BASE_URL silently bakes in the http://localhost:8000/api/v1 fallback from
// src/lib/api.ts. That points at whichever machine happens to be *viewing* the site, so the
// deploy succeeds and only fails once a visitor loads it. Fail the build instead.
//
// Only hosted builders are gated: a local `npm run build` is a legitimate way to test a
// production bundle against a local backend, and should keep working without the variable.
const HOSTED_BUILDER = ["VERCEL", "RENDER", "CI"];

const withApiBaseUrlCheck = (phase: string): NextConfig => {
  const isHostedBuild =
    phase === PHASE_PRODUCTION_BUILD &&
    HOSTED_BUILDER.some((name) => process.env[name]);

  if (isHostedBuild && !process.env.NEXT_PUBLIC_API_BASE_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set for this build.\n\n" +
        "Set it to the deployed API's URL including the /api/v1 suffix, e.g.\n" +
        "  https://specguard-api-ngrt.onrender.com/api/v1\n\n" +
        "On Vercel these are scoped per environment: tick Production, Preview and " +
        "Development, otherwise only some builds pick the value up. Next.js inlines it at " +
        "build time, so redeploy after changing it — restarting is not enough.",
    );
  }

  return nextConfig;
};

export default withApiBaseUrlCheck;
