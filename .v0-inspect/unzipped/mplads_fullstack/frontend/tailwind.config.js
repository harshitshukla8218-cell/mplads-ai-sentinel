/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#14213D",
          700: "#2A3555",
          500: "#48557A",
        },
        paper: {
          50: "#F2F0EA",
          100: "#FFFFFF",
        },
        gold: {
          600: "#B8862E",
          100: "#F7E7C6",
        },
        signal: {
          red: "#B23A2E",
          redlight: "#F6DAD3",
          green: "#3F7A56",
          greenlight: "#DCEEE3",
        },
        line: "#DDD6C6",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
}
