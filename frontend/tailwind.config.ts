import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#183833",
        moss: "#317565",
        mint: "#dceee5",
        coral: "#d36b53",
        paper: "#f7f8f3",
        lavender: "#eeebfa",
        "soft-emerald": "#dff2e9",
        "calm-slate": "#596779",
      },
      fontFamily: {
        sans: ["Avenir Next", "Segoe UI", "sans-serif"],
        serif: ["Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;