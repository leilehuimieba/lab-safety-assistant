/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.ts',
  ],
  theme: {
    extend: {
      colors: {
        risk: {
          low: '#22c55e',
          'medium-low': '#84cc16',
          medium: '#eab308',
          high: '#f97316',
          critical: '#ef4444',
        },
        decision: {
          allow: '#16a34a',
          review: '#d97706',
          block: '#dc2626',
        },
        sidebar: {
          bg: '#1e293b',
          text: '#e2e8f0',
          active: '#2563eb',
          hover: '#334155',
        },
      },
    },
  },
  plugins: [],
};
