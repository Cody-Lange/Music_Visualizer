/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0A0A0F",
          secondary: "#12121A",
          tertiary: "#1A1A28",
        },
        border: "#2A2A3A",
        text: {
          primary: "#F0F0F5",
          secondary: "#8888AA",
        },
        accent: {
          DEFAULT: "#7C5CFC",
          hover: "#9B7FFF",
        },
        success: "#34D399",
        warning: "#FBBF24",
        error: "#F87171",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
