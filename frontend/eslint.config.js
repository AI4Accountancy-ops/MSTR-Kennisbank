import { defineConfig } from 'eslint/config';
import globals from 'globals';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import pluginReact from 'eslint-plugin-react';
import prettierPlugin from 'eslint-plugin-prettier';
import prettierConfig from 'eslint-config-prettier';

export default defineConfig([
  js.configs.recommended,
  tseslint.configs.recommended,
  prettierConfig,
  {
    files: ['**/*.{js,ts,jsx,tsx}'],
    ignores: ['node_modules', 'build', 'dist', 'eslint.config.js'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: ['./tsconfig.app.json', './tsconfig.node.json'],
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: globals.browser,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      react: pluginReact,
      prettier: prettierPlugin,
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/jsx-no-target-blank': ['warn', { enforceDynamicLinks: 'always' }],
      'prettier/prettier': ['warn'],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@mui/material',
              message: 'MUI is deprecated in this project. Use Shadcn UI components instead.',
            },
            {
              name: '@mui/material/styles',
              message: 'MUI is deprecated in this project. Use Tailwind/Shadcn theme utilities.',
            },
            {
              name: '@mui/icons-material',
              message: 'Use lucide-react icons instead of MUI icons.',
            },
            {
              name: '@emotion/react',
              message: 'Emotion is deprecated. Use Tailwind/Shadcn styling.',
            },
            {
              name: '@emotion/styled',
              message: 'Emotion is deprecated. Use Tailwind/Shadcn styling.',
            },
          ],
          patterns: [
            {
              group: ['@mui/*', '@emotion/*'],
              message: 'MUI/Emotion are deprecated. Use Shadcn and Tailwind.',
            },
          ],
        },
      ],
    },
  },
]);
