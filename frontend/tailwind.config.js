/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vscode-bg': '#1e1e1e',
        'vscode-sidebar': '#252526',
        'vscode-border': '#3e3e42',
        'vscode-hover': '#2a2d2e',
        'vscode-text': '#cccccc',
        'vscode-blue': '#007acc',
      },
      fontFamily: {
        mono: ['Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}

