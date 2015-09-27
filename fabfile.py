import json
from datetime import date
from fabric.api import lcd, local

unreleased = """
## [Unreleased]
---

### New

### Changes

### Fixes
"""


def freeze():
    """
    freezes pip requirements
    """
    local("pip freeze > requirements.txt")


def bootstrap():
    """Sets up certain environment commands"""
    local('git config commit.template templates/git-commit-template.txt')

def _get_current_version():
    with open('bower.json', 'r') as bower_file:
        bower_data = bower_file.read()
        bower_info = json.loads(bower_data)
    return bower_info['version']


def update_version(type='patch', commit=True):
    """
    updates the version of the app
    patch, minor, major
    """
    version = _get_current_version()
    major, minor, patch = version.split('.')
    major = int(major)
    minor = int(minor)
    patch = int(patch)
    if type == "patch":
        patch += 1
    if type == "minor":
        minor += 1
        patch = 0
    if type == "major":
        major += 1
        minor = 0
        patch = 0
    new_version = "{0}.{1}.{2}".format(major, minor, patch)
    if commit:
        with open('bower.json', 'r') as bower_file:
            bower_data = json.loads(bower_file.read())
        bower_data['version'] = new_version
        with open('bower.json', 'w') as bower_file:
            bower_file.write(json.dumps(bower_data, indent=4, separators=(',', ': ')))
        with open('package.json', 'r') as node_file:
            node_data = json.loads(node_file.read())
        node_data['version'] = new_version
        with open('package.json', 'w') as node_file:
            node_file.write(json.dumps(node_data, indent=4, separators=(',', ': ')))
    else:
        return new_version


def _changelog(new_version):
    today = date.today()
    outfile = []
    with open("CHANGELOG.md", 'r') as cfile:
        changelog = cfile.read().split('\n')
        for line in changelog:
            if line == "## [Unreleased]":
                line = "## [%s] - %s" % (new_version, today)
            outfile.append(line)
        outfile.insert(4, unreleased)
    with open("CHANGELOG.md", 'w') as cfile:
        cfile.write('\n'.join(outfile) + '\n')


def release(type='patch'):
    """
    Start a `git flow release`, Updates version, changes the set
    """
    new_version = update_version(type=type, commit=False)
    local("git flow release start %s" % new_version)
    update_version(type=type)
    _changelog(new_version)
    local("git add .")
    local("git commit -m 'update for release'")
    local("git flow release finish %s" % new_version)
    local("git push --tags")
    local("git push --all")


def prepare_assets():
    local('npm install')
    local("bower install")
    compile_scss()


def compile_scss():
    with lcd('static/assets/styles'):
        local('python -mscss styles.scss > styles.css')


def start():
    local("python main.py")


def test():
    local("python tests.py")