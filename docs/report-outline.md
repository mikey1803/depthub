# Report outline: DeptHub

Structure matches the assignment. Fill each section from the notes below.

## 1. Title
**DeptHub: an Auto-Updating Department Portal Deployed to Azure with Terraform and Jenkins CI/CD**
Your name, register number, course, department, date.

## 2. Objective
- Provision cloud infrastructure on Azure as code (Terraform).
- Build a Jenkins pipeline that checks out code from GitHub, builds it and deploys it to the Azure VM with no manual steps.
- Achieve continuous deployment: every commit to `main` reaches the live site automatically.
- Add safety: tests, data validation, health check and automatic rollback.

## 3. Tools Used
| Tool | Purpose |
|---|---|
| Microsoft Azure | Cloud platform (VM, network) |
| Terraform (azurerm provider) | Infrastructure as Code |
| cloud-init | First-boot setup of the VM |
| Jenkins | CI/CD server |
| GitHub + webhook | Source control and build trigger |
| Python, Flask, Jinja | Web application |
| pytest | Automated tests |
| nginx + gunicorn + systemd | Serving the app on the VM |
| Gmail SMTP + Email Extension plugin | Build notifications |
| ngrok (if Jenkins is local) | Lets GitHub reach the webhook |

## 4. Architecture Diagram
Paste the Mermaid diagram from `README.md` (render it at <https://mermaid.live> and export as PNG), and add the release layout on the VM (`releases/`, `current` symlink, `deploy_history.jsonl`).
Explain the flow in 5 sentences: push, webhook, Jenkins stages, scp + ssh, nginx to gunicorn to Flask.

## 5. Terraform Code Snippets
Include short snippets from `terraform/` and one sentence on each:
- `provider "azurerm"` block with `subscription_id`
- `azurerm_resource_group`, `azurerm_virtual_network`, `azurerm_subnet`
- `azurerm_network_security_group` with the port 22 and port 80 rules
- `azurerm_public_ip` and `azurerm_network_interface`
- `azurerm_linux_virtual_machine` (Ubuntu 22.04, Standard_B1s, SSH key, `custom_data`)
- `outputs.tf`
- Key parts of `cloud-init.yaml` (packages, nginx proxy, systemd service)

## 6. Jenkinsfile
Include the full Jenkinsfile (or the `triggers` block and each stage) and explain:
- Triggers: `githubPush()` and `pollSCM('H/2 * * * *')`
- Stage by stage: Checkout, Install & Test, Validate Data, Build Package, Deploy to Azure
- `sshagent(credentials: ['azure-vm-ssh'])`
- `post` blocks for the success and failure emails
Then explain `scripts/deploy.sh`: unpack, venv, symlink switch, restart, health check, rollback, keep last 5.

## 7. Screenshots
See the checklist below.

## 8. Observations
Ideas to write about (use your real numbers):
- How long a commit takes to go live (push to site updated).
- Webhook gave near-instant builds; Poll SCM was the fallback.
- Validation stopped broken JSON before deploy and the site stayed up.
- The health check caught a bad release and rollback restored the old one without manual work.
- The symlink switch makes the cutover almost instant and makes rollback trivial.
- Problems you hit and how you fixed them (SKU capacity, SSH key format, SMTP app password, etc.).
- Cost: B1s VM plus public IP, and why `terraform destroy` matters.

## 9. Conclusion
Summarise what was achieved against the objectives, and mention possible future work: HTTPS with a certificate, a staging environment, a Terraform remote state, containerising with Docker, a managed database for notices.

---

## Screenshot checklist

- [ ] `terraform apply` output, with the final outputs (public IP, SSH command, site URL)
- [ ] Azure portal: the resource group with all resources listed
- [ ] Azure portal: the NSG showing the port 22 and 80 rules (optional but nice)
- [ ] Jenkins job page: build success with the **Stage View** (all stages green)
- [ ] Jenkins console output of the deploy stage (health check passing)
- [ ] GitHub webhook page showing a green tick on a recent delivery
- [ ] Live site on the Azure IP: notice board with an urgent notice, and the version badge in the footer
- [ ] Student showcase with a skill filter applied
- [ ] A notice detail page with its QR code
- [ ] Deployment history page (`/deploys`) with several rows
- [ ] **Rollback demo:** the failed Jenkins build (red stage, "rolled back" in the console), AND the site still up, with `/deploys` showing a `rolled-back` row
- [ ] Validation failure: a build stopped at **Validate Data** with the error message
- [ ] The success email received, and the failure email received
