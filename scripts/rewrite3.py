import subprocess
import os

def run(cmd):
    return subprocess.check_output(cmd, encoding='utf-8')

# Get the list of commits from origin/main (which had the right files before all these rewrites)
# Wait, the current branch has the correct files.
commits = run(['git', 'log', '--format=%H', '9f1d417..HEAD']).strip().split('\n')[::-1]

subprocess.check_call(['git', 'reset', '--hard', '9f1d417'])

for commit in commits:
    # Cherry pick
    subprocess.check_call(['git', 'cherry-pick', commit])
    
    # Get message
    msg = run(['git', 'log', '-1', '--format=%B'])
    
    # Ensure Co-authored by snaha is there
    if 'Co-authored-by: snahadhar18' not in msg:
        msg = msg.strip() + '\n\nCo-authored-by: snahadhar18 <snahadhar18@users.noreply.github.com>\n'
    
    # Remove any cursor agent stuff
    msg = msg.replace('Co-authored-by: Prakhar SHUKLA <pss317@uowmail.edu.au>', '')
    msg = msg.replace('- Added .cursor/ to .gitignore\n', '')
    msg = msg.replace('- Added .cursor/ to .gitignore', '')
    
    # Clean up empty lines
    msg = '\n'.join([line for line in msg.split('\n') if line.strip() != ''])
    
    with open('msg.txt', 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    
    # Amend with new author
    subprocess.check_call(['git', 'commit', '--amend', '-F', 'msg.txt', '--author=Prakhar SHUKLA <pss317@uowmail.edu.au>'])

print("Done")
