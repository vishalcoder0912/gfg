/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        body: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        ink: {
          50: "#f6f7f8",
          100: "#e9edf0",
          200: "#ced6dc",
          300: "#a7b4bf",
          400: "#748898",
          500: "#4b6578",
          600: "#365163",
          700: "#2a3f4e",
          800: "#233441",
          900: "#1d2c36"
        },
        sand: {
          50: "#fffaf0",
          100: "#fff1d6",
          200: "#ffe1ad",
          300: "#ffc972",
          400: "#ffad3d",
          500: "#ff8f1a",
          600: "#e86f00",
          700: "#bf5400",
          800: "#9b4300",
          900: "#7e3700"
        }
      },
      boxShadow: {
        soft: "0 10px 30px rgba(0,0,0,0.08)"
      }
    }
  },
  plugins: []
};
