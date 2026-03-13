import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooks,
    },
    languageOptions: {
      globals: { ...globals.browser, ...globals.es2020 },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react/react-in-jsx-scope': 'off',  // React 17+ JSX transform
      'react/prop-types': 'off',           // project doesn't use prop-types
    },
  },
  {
    // Ignore test files and config files from strict rules
    files: ['**/*.test.{js,jsx}', 'vite.config.js', 'test-setup.js'],
    rules: { 'no-unused-vars': 'warn' },
  },
];
