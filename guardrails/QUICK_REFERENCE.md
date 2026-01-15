# Quick Reference: Syntax Checking

## Before Any Deployment or After Refactoring

```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
bash find_all_syntax_errors.sh
```

**If errors found:** Fix ALL errors, then run again to verify.

**If import fails:** Check the error message - usually missing imports or NameError.

## Full Documentation

See `guardrails/SYNTAX_CHECKING.md` for complete documentation.

## Key Principle

**Find ALL errors at once, fix ALL errors at once.** Don't debug one syntax error at a time.

