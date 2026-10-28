#!/bin/bash
# One-time helper: set a new password for a Jenkins user (Jenkins' own user database).
# Run inside WSL as root, from Windows PowerShell in the project folder:
#   wsl -d Ubuntu-22.04 -u root bash scripts/jenkins-reset-password.sh
# The password is typed at a hidden prompt, applied by a one-shot Jenkins init script during a
# restart, and the temporary files delete themselves. Jenkins security stays ON the whole time.
set -e
JH=/var/lib/jenkins

echo "Existing Jenkins users:"
ls "$JH/users" 2>/dev/null | grep -v users.xml | sed 's/_[0-9]*$//; s/^/  /' || true
echo

read -r -p "Username to reset [mikey1803]: " u
u="${u:-mikey1803}"
read -r -s -p "New password (hidden): " p1; echo
read -r -s -p "Repeat new password (hidden): " p2; echo
if [ "$p1" != "$p2" ]; then echo "The two passwords do not match. Nothing was changed."; exit 1; fi
if [ "${#p1}" -lt 8 ]; then echo "Please use at least 8 characters. Nothing was changed."; exit 1; fi

# temporary, root/jenkins-only files
printf '%s\n%s' "$u" "$p1" > "$JH/.pw-reset"
chown jenkins:jenkins "$JH/.pw-reset"; chmod 600 "$JH/.pw-reset"
install -d -m 755 -o jenkins -g jenkins "$JH/init.groovy.d"
cat > "$JH/init.groovy.d/zz-pw-reset.groovy" <<'GROOVY'
import hudson.model.User
import hudson.security.HudsonPrivateSecurityRealm
def f = new File('/var/lib/jenkins/.pw-reset')
try {
  if (f.exists()) {
    def lines = f.readLines()
    def user = User.getById(lines[0], false)
    if (user != null) {
      user.addProperty(HudsonPrivateSecurityRealm.Details.fromPlainPassword(lines[1]))
      user.save()
      println "DeptHub: password reset for user ${lines[0]}"
    } else {
      println "DeptHub: no Jenkins user called ${lines[0]}"
    }
  }
} finally {
  f.delete()
  new File('/var/lib/jenkins/init.groovy.d/zz-pw-reset.groovy').delete()
}
GROOVY
chown jenkins:jenkins "$JH/init.groovy.d/zz-pw-reset.groovy"

echo "Restarting Jenkins to apply the new password (about 1 minute)..."
systemctl restart jenkins
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8080/login || true)
  if [ "$code" = "200" ]; then break; fi
  sleep 3
done

if [ -e "$JH/.pw-reset" ] || [ -e "$JH/init.groovy.d/zz-pw-reset.groovy" ]; then
  echo "Jenkins did not apply the reset yet (temporary files still there). Wait a minute and check http://localhost:8080"
else
  echo "Done. Log in at http://localhost:8080 as '$u' with your new password."
fi
grep -h "DeptHub: " /var/log/jenkins/jenkins.log 2>/dev/null | tail -1 || true
