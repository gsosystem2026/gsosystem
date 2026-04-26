/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.py",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#1152d4",
        "background-light": "#f6f6f8",
        "background-dark": "#101622",
      },
      fontFamily: {
        display: ["Public Sans", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/container-queries"),
  ],
};
