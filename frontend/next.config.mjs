/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async headers() {
    const connectSrc = [
      "'self'",
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
      "http://localhost:8000",
      "http://127.0.0.1:8000",
      "ws://localhost:8000",
      "ws://127.0.0.1:8000",
      "http://localhost:1234",
      "http://127.0.0.1:1234",
      "http://localhost:11434",
      "http://127.0.0.1:11434",
      "http://localhost:8080",
      "http://127.0.0.1:8080",
      "http://localhost:30000",
      "http://127.0.0.1:30000",
    ].join(" ");

    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=(), payment=(), usb=()" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              `connect-src ${connectSrc}`,
              "font-src 'self' data:",
              "media-src 'self' blob:",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
