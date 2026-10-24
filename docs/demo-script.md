# 2-minute live demo script

**Before you start (do once):** site open in one tab at `http://<VM-IP>/`, `/deploys` in another, Jenkins job page open next to it, your mailbox open. Make sure the last build is green. Have `data/notices.json` open in your editor.

## Part 1: a normal deploy (about 70 seconds)

| Time | Say | Do |
|---|---|---|
| 0:00 | "DeptHub is our department portal. Content is just JSON in GitHub, and the site updates itself. Here is the current notice board." | Show the live site, point at the version badge in the footer. |
| 0:15 | "I'll post a new urgent notice." | In `data/notices.json` add a notice (copy an existing one, new `id`, `"urgent": true`, `expires_on` in the future). Save. |
| 0:30 | "One commit and one push. That is all I do." | `git commit -am "Add urgent notice"` then `git push`. |
| 0:40 | "GitHub's webhook just told Jenkins. It runs the tests, validates the data, packages the app, and deploys it to Azure over SSH." | Switch to Jenkins; show the stage view filling up. |
| 1:00 | "Deploy script switches a symlink, restarts the service and checks `/health`." | Point at the Deploy stage turning green. |
| 1:05 | "Refresh the site: the new notice is pinned in red, and the badge shows the new build number." | Refresh the site. Open `/deploys` and show the new row. |
| 1:15 | "And the email lands too." | Show the "New DeptHub deploy live" email. |

## Part 2: a bad commit (about 45 seconds)

**2a. Validation catches it (before anything is deployed)**

| Time | Say | Do |
|---|---|---|
| 1:20 | "Now someone makes a mistake: a category that doesn't exist." | Change a notice's `"category"` to `"Gossip"`. Commit and push. |
| 1:35 | "Jenkins stops before anything is deployed. The test suite already checks the real data files, so it fails at Install & Test with the exact problem. Validate Data is a second safety net behind it. The live site is untouched." | Show the red **Install & Test** stage (later stages are skipped) and the console line `unknown category 'Gossip'`. Refresh the site: still fine. Show the failure email. |

**2b. Rollback catches it (if the bad data gets past the checks)**

Pre-step: on the Jenkins job, use **Build with Parameters** and tick **SKIP_CHECKS** (this demo switch skips tests and validation, to simulate a mistake nobody caught).

| Time | Say | Do |
|---|---|---|
| 1:45 | "Let's pretend the checks were skipped and the broken data reaches the server." | Build with Parameters, `SKIP_CHECKS` ticked (the bad commit from 2a is still the latest). |
| 2:00 | "The new release fails its health check, so deploy.sh moves the symlink back to the previous version, restarts, and fails the build." | Show the console: health check failing, then "Rolling back". |
| 2:10 | "The site never went down: still the last good version." | Refresh the site. Show `/deploys` with the `rolled-back` row. |

**Clean up after the demo:** revert the bad commit (`git revert HEAD`, `git push`) so `main` is healthy again.

## Tips
- Which stage fails first on bad data: `tests/test_validate.py::test_real_repo_data_passes` runs the validator on the real `data/` folder, so **Install & Test** catches it before **Validate Data** even runs. Both use the same rules (`scripts/validate_data.py`).
- Rehearse once. A deploy takes about a minute because pip installs the packages into a fresh venv.
- If the webhook is slow (ngrok), click **Build Now**; mention that Poll SCM is the safety net.
- Part 2b is the long one. If you are short on time, show it from a recorded run or screenshot.
