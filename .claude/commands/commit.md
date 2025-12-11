Run sanity tests, then commit staged changes using the project format:

1. First run `./test.sh sanity` to verify tests pass
2. Run `git status` and `git diff --staged` to review changes
3. Commit with format: `[chef] [context] max-6-words-comment`

Context should be one word describing the area: renderer, slang, ci, tests, cli, model, etc.

Examples:
- `[chef] [renderer] fix table header column names`
- `[chef] [slang] add nested struct lookup`
- `[chef] [ci] replace codecov with artifacts`
