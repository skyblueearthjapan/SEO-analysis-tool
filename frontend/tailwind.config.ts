import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Midnight Neon Theme
        'bg-base': '#0f1729',
        'bg-surface': '#1a2744',
        'bg-elevated': '#243351',
        'accent-cyan': '#35D4FF',
        'accent-violet': '#A78BFA',
        'accent-green': '#4ADE80',
        'accent-amber': '#FBBF24',
        'accent-red': '#F87171',
        'text-primary': '#F1F5F9',
        'text-secondary': '#94A3B8',
        'text-muted': '#64748B',
      },
      fontFamily: {
        sans: ['Noto Sans JP', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(53, 212, 255, 0.15)',
        'glow-violet': '0 0 20px rgba(167, 139, 250, 0.15)',
      },
      backdropBlur: {
        'glass': '12px',
      },
    },
  },
  plugins: [],
}
export default config
