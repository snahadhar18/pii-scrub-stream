import subprocess
import os

def run(cmd):
    return subprocess.check_output(cmd, encoding='utf-8')

# Get the list of commits from 9f1d417..HEAD
commits = run(['git', 'log', '--format=%H', '9f1d417..HEAD']).strip().split('\n')[::-1]

subprocess.check_call(['git', 'reset', '--hard', '9f1d417'])

for commit in commits:
    # Cherry pick
    subprocess.check_call(['git', 'cherry-pick', commit])
    
    # Get message
    msg = run(['git', 'log', '-1', '--format=%B'])
    
    # Ensure Co-authored by Prakhar is there
    if 'Co-authored-by: snahadhar18' in msg:
        msg = msg.replace('Co-authored-by: snahadhar18 <snahadhar18@users.noreply.github.com>', 'Co-authored-by: Prakhar SHUKLA <pss317@uowmail.edu.au>')
    elif 'Co-authored-by: Prakhar SHUKLA' not in msg:
        msg = msg.strip() + '\n\nCo-authored-by: Prakhar SHUKLA <pss317@uowmail.edu.au>\n'
    
    # Clean up any leftover cursor references just in case
    msg = msg.replace('remove cursor agent references', '')
    
    with open('msg.txt', 'w', encoding='utf-8') as f:
        f.write(msg + '\n')
    
    # Amend with new author
    subprocess.check_call(['git', 'commit', '--amend', '-F', 'msg.txt', '--author=snahadhar18 <snahadhar18@users.noreply.github.com>'])

print("Done")
