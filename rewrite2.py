import subprocess
import os

def run(cmd):
    return subprocess.check_output(cmd, encoding='utf-8')

# Get the list of commits to rewrite
commits = run(['git', 'log', '--format=%H', '9f1d417..HEAD']).strip().split('\n')[::-1]

# Save current gitignore just in case
with open('.gitignore', 'r', encoding='utf-8') as f:
    current_gitignore = f.read()

# Reset to base
subprocess.check_call(['git', 'reset', '--hard', '9f1d417'])

env = os.environ.copy()
env['GIT_AUTHOR_NAME'] = 'Prakhar SHUKLA'
env['GIT_AUTHOR_EMAIL'] = 'pss317@uowmail.edu.au'
env['GIT_COMMITTER_NAME'] = 'Prakhar SHUKLA'
env['GIT_COMMITTER_EMAIL'] = 'pss317@uowmail.edu.au'

for commit in commits:
    # Get original message
    msg = run(['git', 'log', '-1', '--format=%B', commit])
    
    # Modify message
    msg = msg.replace('Co-authored-by: Prakhar SHUKLA <pss317@uowmail.edu.au>', 'Co-authored-by: snahadhar18 <snahadhar18@users.noreply.github.com>')
    msg = msg.replace('- Added .cursor/ to .gitignore\n', '')
    msg = msg.replace('- Added .cursor/ to .gitignore', '')
    
    with open('msg.txt', 'w', encoding='utf-8') as f:
        f.write(msg.strip() + '\n')
    
    # Cherry pick
    subprocess.check_call(['git', 'cherry-pick', commit])
    
    # Amend with new author and message
    subprocess.check_call(['git', 'commit', '--amend', '-F', 'msg.txt'], env=env)

# Finally, ensure .gitignore is correct
with open('.gitignore', 'w', encoding='utf-8') as f:
    f.write(current_gitignore)
subprocess.check_call(['git', 'add', '.gitignore'])
subprocess.check_call(['git', 'commit', '--amend', '--no-edit'], env=env)

print("Rewrite complete.")
