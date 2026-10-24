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
