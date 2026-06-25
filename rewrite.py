import subprocess
import sys

def run(cmd):
    print("Running:", cmd)
    return subprocess.check_output(cmd, encoding='utf-8')

# Set environment variables for the author to override it for all commits during rebase
import os
env = os.environ.copy()
env['GIT_AUTHOR_NAME'] = 'snahadhar18'
env['GIT_AUTHOR_EMAIL'] = 'snahadhar18@users.noreply.github.com'

# Actually it's easier to just do: git rebase -x "git commit --amend --reset-author -C HEAD"
# but since the committer is already Prakhar SHUKLA (from global git config), if we set the env vars for author, it will work.

print("Rebasing...")
subprocess.check_call(
    ['git', 'rebase', '--exec', 'git commit --amend --author="snahadhar18 <snahadhar18@users.noreply.github.com>" --no-edit', '9f1d417'],
    env=env
)

print("Updating last commit message...")
log = run(['git', 'log', '-1', '--format=%B'])
new_log = log.replace("remove cursor agent references", "").strip()
with open("msg.txt", "w", encoding='utf-8') as f:
    f.write(new_log)

subprocess.check_call(
    ['git', 'commit', '--amend', '-F', 'msg.txt', '--author=snahadhar18 <snahadhar18@users.noreply.github.com>']
)

print("Done")
