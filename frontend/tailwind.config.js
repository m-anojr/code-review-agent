/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0d1117',
          raised: '#161b22',
          overlay: '#21262d',
        },
        border: {
          DEFAULT: '#30363d',
          muted: '#21262d',
        },
        text: {
          primary: '#e6edf3',
          secondary: '#8b949e',
          muted: '#484f58',
        },
        accent: '#58a6ff',
        severity: {
          critical: '#f85149',
          high: '#d29922',
          medium: '#58a6ff',
          low: '#8b949e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
};
