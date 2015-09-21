Fabric Commands
===============

Here are a list of the usable fabric commands for this project.


### freeze

This is a shortcut command to dump the pip requirements to `requirements.txt`.

It wraps `pip freeze > requirements.txt`


### bootstrap

This is a shortcut command to setup git commit templating.


### compile_scss

This command compiles the styles scss to css.

### prepare_assets

This command runs `npm install`, `bower install`, and compiles the scss.

### release

Takes `type` argument with options of `patch`, `minor`, and `major`.

