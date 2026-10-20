/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
    '../../**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          emerald: '#059669',
          'emerald-dark': '#047857',
          orange: '#F97316',
          'orange-hover': '#C2410C',
          'orange-light': '#FFEDD5',
        }
      }
    },
  },
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
    themes: [
      {
        light: {
          "primary": "#059669",        // Émeraude principal
          "primary-focus": "#047857",  // Émeraude hover
          "secondary": "#F97316",      // Orange principal
          "secondary-focus": "#C2410C",// Orange hover
          "accent": "#FFEDD5",         // Orange clair
          "neutral": "#1C1917",        // Texte clair
          "base-100": "#FAFAF9",       // Fond clair (blanc cassé)
          "base-200": "#F5F5F4",
          "base-300": "#E7E5E4",
        },
        dark: {
          "primary": "#059669",        // Émeraude principal
          "primary-focus": "#047857",
          "secondary": "#F97316",      // Orange principal
          "secondary-focus": "#C2410C",
          "accent": "#FFEDD5",
          "neutral": "#F5F5F4",        // Texte sombre
          "base-100": "#0F1712",       // Fond sombre (noir émeraude)
          "base-200": "#16221B",
          "base-300": "#1F2E25",
        },
      },
    ],
  },
}
