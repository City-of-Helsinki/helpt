[![Build status](https://travis-ci.org/City-of-Helsinki/helpt.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/helpt)
[![codecov](https://codecov.io/gh/City-of-Helsinki/helpt/branch/master/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/helpt)

Installation
------------

Install required Python packages

```
pip install -r requirements.txt
```

Install node dependencies

```
npm install
```

Install bower components

```
./manage.py bower install
```

Requirements
------------

This project uses two files for requirements. The workflow is as follows.

`requirements.txt` is not edited manually, but is generated
with `pip-compile`.

`requirements.txt` always contains fully tested, pinned versions
of the requirements. `requirements.in` contains the primary, unpinned
requirements of the project without their dependencies.

In production, deployments should always use `requirements.txt`
and the versions pinned therein. In development, new virtualenvs
and development environments should also be initialised using
`requirements.txt`. `pip-sync` will synchronize the active
virtualenv to match exactly the packages in `requirements.txt`.

In development and testing, to update to the latest versions
of requirements, use the command `pip-compile`. You can
use [requires.io](https://requires.io) to monitor the
pinned versions for updates.

To remove a dependency, remove it from `requirements.in`,
run `pip-compile` and then `pip-sync`. If everything works
as expected, commit the changes.
