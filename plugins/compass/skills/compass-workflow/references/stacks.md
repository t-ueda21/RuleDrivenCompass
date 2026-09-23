# Stack notes

Select a stack from the project profile or by inspecting project files. More than one stack may apply. Treat these notes as questions to check, not a mandate to replace the project's toolchain.

| Stack | Look for | Check |
| --- | --- | --- |
| Common | README and existing scripts | Follow documented runtime, formatting, test, and build commands. |
| Python | pyproject.toml, requirements files, tox.ini | Keep the current interpreter and package manager; run the project's test and lint commands. |
| FastAPI | FastAPI imports, ASGI entry point | Check request and response schemas, status codes, dependency handling, and API tests. |
| Node.js | package.json and lockfile | Use the package manager matching the lockfile and existing scripts. |
| TypeScript | tsconfig.json | Preserve strictness and type boundaries; run type checking when configured. |
| React | React components and UI test setup | Check state, accessibility, empty/error states, and relevant UI tests. |
| Electron | Electron main/preload/renderer split | Respect process boundaries and preload exposure; avoid widening IPC access. |
| Tauri | src-tauri and frontend config | Check Rust commands and frontend scripts; preserve the existing bridge boundary. |
| Playwright | playwright.config.* | Use configured projects, fixtures, and test-data cleanup. |
| CDP/browser automation | browser driver setup | Follow the existing browser lifecycle and avoid fixed sleeps where state waits exist. |
| LLM | provider/model configuration | Preserve the configured provider, avoid logging prompts or credentials, and verify fallbacks. |
| Search | index/schema configuration | Check tokenization, ranking expectations, and index rebuild behavior. |
| Database | migrations and schema files | Preserve existing rows, test migrations, and check rollback or recovery expectations. |
| Go | go.mod | Use existing Go version and modules; run focused go test commands. |
| Rust | Cargo.toml | Use existing features and targets; run focused cargo test/check commands. |
| .NET | solution/project files | Follow target frameworks and existing dotnet test/build commands. |
| Java | Maven or Gradle files | Use the repository's wrapper and configured test tasks. |
| Docker | Dockerfile or compose files | Do not start or publish services unless requested; use existing validation commands. |

When stack evidence conflicts with a profile, note the mismatch and follow the project files that define the active build. Update project-local configuration only when the user asks to change the stack or when initialization creates a missing profile.
