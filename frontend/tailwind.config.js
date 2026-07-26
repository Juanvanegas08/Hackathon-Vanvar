/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        casa: {
          bg: '#faf9f6',
          ink: '#12141a',
          muted: '#5c6370',
          yellow: '#f5c518',
          'yellow-soft': '#ffe56a',
          blue: '#1e3a5f',
          green: '#3d8b6e',
          surface: '#ffffff',
          line: '#e8e6df',
        },
      },
    },
  },
  plugins: [],
}
