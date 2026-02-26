# Fix EC2 deploy failure: /etc/environment and dpkg

If the backend deploy fails with:

```text
/usr/sbin/update-info-dir: 8: /etc/environment: 832#: not found
dpkg: error processing package install-info (--configure): ... exit status 127
```

the EC2 server has a bad line in `/etc/environment` (e.g. a stray `832#` or line number) that breaks package scripts. Fix it once on the server, then re-run the deploy.

## Steps on the EC2 server

1. **SSH into the backend server** (same host/key you use for deploys).

2. **Inspect and fix `/etc/environment`:**
   ```bash
   sudo cat /etc/environment
   ```
   Remove or fix any line that looks wrong (e.g. `832#`, a lone number, or garbage). The file should only have simple `KEY="value"` lines, one per line, e.g.:
   ```text
   PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
   ```

   Edit (use nano or vim):
   ```bash
   sudo nano /etc/environment
   ```
   Save and exit.

3. **Finish interrupted package configuration:**
   ```bash
   sudo dpkg --configure -a
   ```

4. **Re-run the GitHub Action** (Actions → Deploy Agents Backend → Re-run all jobs).

The workflow was also updated to skip `apt-get install jq` when `jq` is already installed, so the deploy may succeed even before fixing the server if jq was already there.
