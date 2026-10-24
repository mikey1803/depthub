# Setup log

A running record of how DeptHub was taken from code to a live deployment. Useful for the report's *Observations* section.

## 2026-10-24: Preparing the tools

| Step | What happened |
|---|---|
| Local git repo | `git init -b main`, first commit with 34 files. Checked beforehand that `.gitignore` excludes `.venv`, `version.json`, `*.tfvars` and `*.tfstate`, and that no secret-like files were tracked. |
| Line endings | Added `.gitattributes` forcing LF. The project is written on Windows but runs on Linux (Jenkins in WSL2 and the Azure VM), and a CRLF `deploy.sh` would fail there. |
| GitHub CLI | Installed `gh` 2.103.2 with winget. Login uses the browser device-code flow (done by the user). |
| Terraform | Installed 1.16.6 with winget. |
| SSH key | Generated an RSA 4096 key pair `~/.ssh/depthub_key` (Azure Linux VMs only accept RSA keys). The private key stays on this machine and is never committed. |
| Azure CLI | Installing 2.91.0 with winget. |
| WSL2 | Only the `docker-desktop` distro existed, so Ubuntu 22.04 is being installed for Jenkins. |
