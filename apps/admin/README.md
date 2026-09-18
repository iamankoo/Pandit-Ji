# admin

Pandit Ji internal admin app — rule authoring/versioning, content ops (`docs/ARCHITECTURE.md` §"Repository Structure"). Shares the web app's Next.js/React/TypeScript stack (`TECH_STACK.md`).

## Phase 3 status

Foundation only: placeholder home page, TypeScript/ESLint/Prettier/Vitest configured and passing. No admin screens yet.

## Local development

```
npm install
npm run dev
```

Runs on port 3001 by default (distinct from `apps/web`'s 3000) so both can run side by side locally.

## Checks

```
npm run typecheck
npm run lint
npm run format
npm test
```
