# React + TypeScript + Vite

## Service health

The dashboard polls `GET /metrics/anomaly-score` every five seconds for live per-service status; anomaly events remain a separate history endpoint.
The backend compares the latest complete minute with a baseline of up to 30 earlier complete minutes, treating quiet minutes as zero.
It computes z-score as `(current errors - baseline mean) / max(baseline standard deviation, 1)`.
Scores below 2 are `NORMAL`, from 2 to below 3 are `WARNING`, and 3 or higher are `ANOMALY`; fewer than five history minutes produce `NO_DATA`.
For example, the backend spike test reports 60 current errors/min, a 3.33 mean, z-score 7.47, and `ANOMALY`.

## Anomaly events

The watcher sends status changes to `POST /anomaly-events`.
The backend saves each event in the `anomaly_events` table.
The dashboard fetches saved events from `GET /anomaly-events` every five seconds.
Events remain available after the watcher stops because they are read from the database.

## Error groups

`GET /error-groups` groups errors by fingerprint, service, and error type, ordered by count; its `minutes` query parameter accepts 1–60 and defaults to 15.
The dashboard refreshes the group list every five seconds and shows the total errors alongside the number of groups.
Grouping repeated errors makes fingerprinting visible and reduces alert noise: an incident is tracked for a group, not created for every individual error.
Only the ten most frequent groups are shown.
Service Health cards with `WARNING` or `ANOMALY` status request the same endpoint with `minutes=5` and show that service's most frequent error group as a hint.
This hint connects the affected service to a likely explanation, but is not a confirmed root cause: the most frequent error may not be the error that triggered the anomaly.

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```

You can also install [eslint-plugin-react-x](https://npmx.dev/package/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://npmx.dev/package/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```
