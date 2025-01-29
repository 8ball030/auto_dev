To install auto_dev, you must have the following installed on your computer:

1.) Python >= 3.10

2.) Poetry < 2.0

a.) You can install Poetry with the following command

  ```
  curl -sSL https://install.python-poetry.org | python - --version 1.8.3
```

replace 1.8.3 with the version you want to install.

3.) [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Installation

Next, please run the following in your terminal:

```console
poetry shell && pip install "autonomy-dev[all]"
```

This is the preferred method to install auto_dev, as it will always install the most recent stable release.

If you don't have [pip][] installed, this [Python installation guide][]
can guide you through the process.

## From source

The source for auto_dev can be downloaded from
the [Github repo][].

You can either clone the public repository:

``` console
$ git clone git://github.com/8ball030/auto_dev
```

Or download the [tarball][]:

``` console
$ curl -OJL https://github.com/8ball030/auto_dev/tarball/master
```

Once you have a copy of the source, you can install it with:

```console
$ pip install .
```

  [pip]: https://pip.pypa.io
  [Python installation guide]: http://docs.python-guide.org/en/latest/starting/installation/
  [Github repo]: https://github.com/%7B%7B%20cookiecutter.github_username%20%7D%7D/%7B%7B%20cookiecutter.project_slug%20%7D%7D
  [tarball]: https://github.com/%7B%7B%20cookiecutter.github_username%20%7D%7D/%7B%7B%20cookiecutter.project_slug%20%7D%7D/tarball/master
