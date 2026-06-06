import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tinker: "#FBB905",
        ink: "#111111",
        bg: "#FFFFFF",
        surface: "#F5F5F4",
        line: "#E5E5E5",
        success: "#16A34A",
        danger: "#DC2626",
      },
    },
  },
  plugins: [],
} satisfies Config;
