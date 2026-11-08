# Homebrew formula for Free My ID

`freemyid.rb` installs the `freemyid` command from the PyPI sdist into its own
virtualenv (`Language::Python::Virtualenv`). It is a draft: it is not published yet.

## Before it can ship (release tooling)
1. Publish the sdist to PyPI. Set `url` and the version to match `pyproject.toml`.
2. Replace the `sha256` placeholder with the sdist's real checksum.
3. Add the dependency `resource` blocks: `brew update-python-resources freemyid`
   (needs network and Homebrew).
4. Check it: `brew audit --strict --new --formula freemyid` and
   `brew install --build-from-source freemyid && brew test freemyid`.

## How the tap will be published (in-house)
The in-house team creates a tap repository (`FreeMyID/homebrew-freemyid`), copies
`freemyid.rb` into its `Formula/` folder, and updates it for each release. Users would then run:

    brew tap FreeMyID/freemyid
    brew install freemyid

Nothing here is "available" until a release is published and `site_src/data/release.yaml`
says so. Homebrew is for people who already use it; Windows users get the installer.

## Try it locally

Status: **coming**. All commands are **unverified** (not run when this was written). They need Homebrew, and
only work after the `sha256` placeholder and the `resource` blocks are filled in.

```
cd distro/homebrew
brew install --build-from-source ./freemyid.rb
brew test freemyid
freemyid --help
brew uninstall freemyid
```

Newer Homebrew may refuse a formula path outside a tap. If so, copy `freemyid.rb` into a tap made with
`brew tap-new local/test` and install `local/test/freemyid`. Not sure this is needed.
