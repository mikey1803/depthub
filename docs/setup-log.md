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
| WSL2 | Only the `docker-desktop` distro existed, so Ubuntu 22.04 was installed for Jenkins. It already runs systemd (PID 1), so no extra setup was needed. |
| GitHub | Logged in with the `gh` device-code flow. Public repo created and pushed: https://github.com/mikey1803/depthub |
| Azure login | The first `az login` used an account with no subscription (`No subscriptions found`). Signing in again with the account that owns the **Azure for Students** subscription fixed it. |
| Terraform | `terraform init` installed azurerm 4.81.0. `terraform plan` gave 8 resources to add. The `az` command was not on the PATH of the already-open shell, so the first plan failed with "az executable not found"; adding the Azure CLI folder to PATH fixed it. |
| Jenkins install | Java 21 (openjdk-21-jre), git, python3, python3-venv and Jenkins 2.580.1 installed in WSL. The current official instructions at pkg.jenkins.io use the `jenkins.io-2026.key` signing key (the README had the old 2023 key; corrected). |

## Azure infrastructure

| Step | What happened |
|---|---|
| First `terraform apply` | 8 resources created in `indiasouthcentral` (VM took 1m23s). Public IP `172.198.62.151`. |
| SSH timed out | Port 80 worked but SSH on port 22 timed out. The VM, agent and NSG rules were all fine. Tests showed the campus network (public IP `14.139.x.x`) blocks **outbound port 22**: `github.com:22` and `gitlab.com:22` were blocked too, from both Windows and WSL, while 443 and 80 worked. On a home network, port 22 worked immediately. |
| Fix: SSH on port 443 | Added an NSG rule `allow-ssh-alt` (port 443), a `ssh_alt_port` variable, and a cloud-init drop-in `/etc/ssh/sshd_config.d/10-depthub.conf` (`Port 22` and `Port 443`). The Jenkinsfile got an `SSH_PORT` setting (parameter, or the `AZURE_SSH_PORT` environment variable, default 22) used for both `scp -P` and `ssh -p`. Login is still key-only. |
| Second `terraform apply` | `1 added, 1 changed, 1 destroyed`: the VM was replaced (changing cloud-init `custom_data` forces a new VM), the NSG was updated in place, and the static public IP stayed the same. Nothing had been deployed yet, so nothing was lost (VM creation took 53s). |
| Verification | SSH worked on both 22 and 443, `scp -P 443` worked, sshd listened on `0.0.0.0:22` and `0.0.0.0:443`, cloud-init status `done`, nginx 1.18 active, `depthub` service enabled, `/opt/depthub/releases` owned by `azureuser`. `http://172.198.62.151/` returned `502 Bad Gateway`, which is correct until the first deploy (nginx is up, the app is not deployed yet). |

## Jenkins configuration

| Step | What happened |
|---|---|
| Start | Jenkins 2.580.1 (Java 21) runs as a systemd service inside WSL2 Ubuntu 22.04 and is reachable from Windows at http://localhost:8080. WSL stops its VM when idle, which would kill Poll SCM, so a hidden `wsl ... sleep infinity` session keeps it alive (it must be restarted after a Windows reboot). |
| Setup wizard | Done by the user in the browser: unlock, "Install suggested plugins", create the admin user `mikey1803` (the password was typed only by the user). |
| Access for automation | The user created an API token and stored it with a hidden terminal prompt in a root-only file inside WSL (`/root/.jenkins-api`). It was never typed into the chat. My first attempt (a long one-line `wsl ... bash -c '...'` command) failed because PowerShell mangled the embedded quotes (`>>` continuation prompt), so a short helper script was used instead. |
| Plugins | The suggested plugins already included Git, GitHub, Pipeline (workflow-aggregator), Email Extension and Credentials. Only **SSH Agent** was missing; it was installed through the update center, which needs a restart before the plugin loads. |
| Provisioning (Jenkins script console) | Created credential `azure-vm-ssh` (user `azureuser`, from the key file; the temporary copy was shredded afterwards), global environment variables `AZURE_VM_IP`, `AZURE_SSH_PORT=443` and `NOTIFY_EMAIL`, Jenkins admin email, Gmail SMTP settings in Extended E-mail (smtp.gmail.com, port 465, SSL), and the pipeline job `depthub` (Pipeline script from SCM, https://github.com/mikey1803/depthub.git, branch `*/main`, `Jenkinsfile`, Poll SCM `H/2 * * * *`). The job was created **disabled** so no build starts before the email password is set. |

## First builds and fixes

| Build | What happened |
|---|---|
| #1 (manual) | Checkout, Install & Test (31 passed), Validate Data and Build Package all passed. **Deploy failed:** `scp ... @172.198.62.151` had an empty user name. On the very first run Jenkins has not read the Jenkinsfile's parameters yet, so `$VM_USER` was empty and ssh fell back to the `jenkins` user (`Permission denied (publickey)`). Fix: `SSH_USER = params.VM_USER ?: 'azureuser'` in the `environment` block. |
| Found while reading #1 | The failure email would have claimed "rolled back to the last working version" even though `deploy.sh` never ran. Fix: the Jenkinsfile now records `ROLLED_BACK` only when `deploy.sh` itself exits with code 1; other failures (build, tests, ssh error) get the message "the live site was not changed". |
| Stray file | While debugging, a PowerShell quoting mistake (`->` inside a string became a shell redirect) created an empty file named `HTTP`, which was committed by accident. Removed in the next commit (it contained nothing). |
| #2 (manual) | **SUCCESS in 40 s.** First real run of `deploy.sh`: unpacked, venv, pip install, symlink switch, restart, health check passed on the 2nd try (gunicorn needs a moment), history entry written, temp files cleaned. The live site showed `v2 · commit d157b67`. |
| #3 (Poll SCM) | Started by an SCM change, triggered by the cleanup commit. SUCCESS. |

## Continuous deployment proof

Notice dates in `data/notices.json` were moved into the future (notice 6 left expired on purpose), committed and pushed at 16:40:57 UTC. Nobody touched Jenkins. At 16:42:15 UTC build #4 started with the cause **"Started by an SCM change"**, checked out commit `5cedf1d`, passed 31 tests and validation, deployed, and finished SUCCESS in 36 s. Push to green: about 1.5 minutes. The live site then showed `v4 · commit 5cedf1d`, 5 visible notices with the new deadlines, notice 6 hidden, and 3 rows on `/deploys`.

## Rollback proof

| Step | Result |
|---|---|
| Bad commit `e6310bb` (category `Gossip`), pushed 16:43:38 UTC | Poll SCM started **#5** by itself. It **failed at Install & Test** (`1 failed, 30 passed`), because `test_real_repo_data_passes` also validates the real data files, so the bad data is caught one stage earlier than the demo script originally said (script corrected). Nothing was deployed; the site stayed on v4. |
| **#6**, started manually with `SKIP_CHECKS=true` | Tests and validation were skipped, so the broken data reached the VM. `/health` returned 500 for all 10 retries. `deploy.sh` printed `ERROR: build 6 failed its health check.` and `Rolling back to /opt/depthub/releases/4`, then `Rollback complete`, removed release 6 and exited 1. Jenkins marked the build FAILURE (`deploy.sh reported a failed deploy: the previous version is still live (rolled back)`). |
| After the rollback | The site never stopped serving v4 (`/health` = `{"build":"4","status":"ok"}`, footer `v4 · commit 5cedf1d`). `/deploys` showed `v6 rolled-back` on top of `v4 success`, `v3`, `v2`. On the VM: `releases/` = 2, 3, 4 and `current -> releases/4`. |
| Restore | `git revert` of the bad commit, pushed 16:49:29 UTC, and picked up by Poll SCM. |

## Other observations

- Jenkins: the Pipeline Stage View plugin is not part of the suggested plugins, so it was installed separately to get the stage-by-stage screenshot.
- `terraform apply` is quick (VM 53 to 83 s), but `az vm list-skus` can take minutes per region because it downloads the whole catalogue.
- A build badge is not possible for a locally hosted Jenkins: GitHub loads README images from its own servers and cannot reach `localhost`. See the README for the public-Jenkins recipe.

## VM size and region

Standard_B1s was not available in Central India for the Azure for Students subscription; VM size and region were parameterized as Terraform variables to switch deployment without code changes.

The subscription also has an "Allowed resource deployment regions" policy that only permits: centralindia, indiasouthcentral, uaenorth, indonesiacentral, malaysiawest. In Central India, every B-series size (including B1s, B2s, and all the `_v2` sizes) carried a `NotAvailableForSubscription` restriction. `terraform plan` cannot detect this; it would only have failed at `apply`.

How it was found:
- `az vm list-skus --size ...` downloads the whole region catalogue and filters on the client, so it took minutes per region and timed out when run for five regions at once. Its `[]` result for Standard_B1s in Central India was misleading: the size exists there, it is just restricted.
- Calling the Azure Compute SKUs REST endpoint directly (`GET /subscriptions/{id}/providers/Microsoft.Compute/skus?$filter=location eq '<region>'`) returned all five regions in seconds and showed the restrictions.

Result (a size is usable only if it has no `NotAvailableForSubscription` restriction):

| Region | Standard_B1s | Standard_B2ats_v2 | Standard_B2s | Standard_D2s_v3 |
|---|---|---|---|---|
| centralindia | restricted | restricted | restricted | restricted |
| **indiasouthcentral** | **available** | available | available | restricted |
| uaenorth | restricted | restricted | restricted | restricted |
| indonesiacentral | restricted | restricted | restricted | restricted |
| malaysiawest | restricted | restricted | restricted | restricted |

vCPU quota was the same in every allowed region (`standardBSFamily` limit 4, none used), so quota was not the blocker.

Decision: keep `Standard_B1s` and move to **India South Central** (Hyderabad) by setting `location = "indiasouthcentral"` in `terraform.tfvars`. No Terraform code change was needed beyond making `image_sku` a variable too.
