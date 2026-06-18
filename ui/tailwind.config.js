export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        jr: {
          bg: '#F5F5F7',
          surface: '#FFFFFF',
          border: '#E5E7EB',
          'border-strong': '#D1D5DB',
          text: '#111111',
          sub: '#6B7280',
          muted: '#9CA3AF',
          accent: '#4F46E5',
          'accent-light': '#EEF2FF',
          green: '#16A34A',
          'green-light': '#F0FDF4',
          amber: '#D97706',
          'amber-light': '#FFFBEB',
          red: '#DC2626',
          'red-light': '#FEF2F2',
          purple: '#7C3AED',
          'purple-light': '#F5F3FF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-in': 'slideIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideIn: { '0%': { opacity: 0, transform: 'translateY(4px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
      }
    }
  },
  plugins: []
}
