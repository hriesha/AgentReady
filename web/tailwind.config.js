/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      keyframes: {
        shimmer: {
          "0%": { transform: "translateX(-120%)" },
          "100%": { transform: "translateX(320%)" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(3px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        bob: {
          "0%, 100%": { transform: "translateY(0) rotate(0deg)" },
          "50%": { transform: "translateY(-4px) rotate(-1.5deg)" },
        },
        ripple: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-40px)" },
        },
        twinkle: {
          "0%, 100%": { opacity: "0" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        shimmer: "shimmer 1.8s ease-in-out infinite",
        fadeIn: "fadeIn 400ms ease-out",
        bob: "bob 3s ease-in-out infinite",
        ripple: "ripple 3s linear infinite",
        twinkle: "twinkle 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
