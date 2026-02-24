/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        surface: {
          DEFAULT: '#0d1117',
          1: '#161b22',
          2: '#1c2128',
          3: '#21262d',
        },
        border: '#30363d',
        accent: {
          green: '#3fb950',
          yellow: '#d29922',
          red: '#f85149',
          blue: '#58a6ff',
          purple: '#bc8cff',
        },
      },
      boxShadow: {
        confirmed: '0 0 12px rgba(63, 185, 80, 0.4)',
        error: '0 0 12px rgba(248, 81, 73, 0.4)',
      },
    },
  },
  plugins: [],
}
