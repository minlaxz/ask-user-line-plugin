```markdown
# ask-user-line-plugin Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill covers the development patterns and conventions used in the `ask-user-line-plugin` repository, a TypeScript codebase with no detected framework. You'll learn about file naming, import/export styles, commit message conventions, and how to write and run tests. This guide also suggests useful commands for common workflows.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `userProfile.ts`, `lineHandler.test.ts`

### Import Style
- Use **relative imports** for referencing other modules.
  - Example:
    ```typescript
    import { getUserProfile } from './userProfile';
    ```

### Export Style
- Use **named exports** rather than default exports.
  - Example:
    ```typescript
    // In userProfile.ts
    export function getUserProfile(id: string) { ... }
    ```

### Commit Messages
- Follow the **Conventional Commits** format.
- Use prefixes like `docs:` for documentation changes.
- Example:
  ```
  docs: update README with usage instructions
  ```

## Workflows

### Writing Code
**Trigger:** When implementing new features or updating logic  
**Command:** `/write-code`

1. Create a new TypeScript file using camelCase (e.g., `newFeature.ts`).
2. Use relative imports to include dependencies.
3. Export functions or constants using named exports.
4. Write clear, concise code following TypeScript best practices.

### Documenting Changes
**Trigger:** When updating or adding documentation  
**Command:** `/document`

1. Make documentation changes in relevant files (e.g., `README.md`).
2. Commit changes with a `docs:` prefix.
   - Example: `docs: add API usage examples to README`
3. Push your changes to the repository.

### Writing Tests
**Trigger:** When adding or updating tests  
**Command:** `/write-test`

1. Create a test file with the `.test.` infix (e.g., `userProfile.test.ts`).
2. Write tests for your code (testing framework is not specified—use your team's standard).
3. Use relative imports to bring in the modules to test.
4. Run the tests using your preferred test runner.

## Testing Patterns

- Test files are named with the `.test.` pattern, such as `lineHandler.test.ts`.
- The testing framework is not specified; follow your team's standard.
- Example test file structure:
  ```typescript
  import { getUserProfile } from './userProfile';

  describe('getUserProfile', () => {
    it('returns user data for valid ID', () => {
      // Test implementation here
    });
  });
  ```

## Commands
| Command       | Purpose                                   |
|---------------|-------------------------------------------|
| /write-code   | Start implementing new code or features   |
| /document     | Update or add documentation               |
| /write-test   | Add or update tests for your code         |
```