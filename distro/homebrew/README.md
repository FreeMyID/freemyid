# Homebrew formula for Free My ID

This is a community recipe. It is not submitted upstream. There is no tap, and it is not in homebrew-core.

`freemyid.rb` would install the `freemyid` command from the PyPI source archive into its own virtualenv (`Language::Python::Virtualenv`). That install was not run.

The app version in this tree is 0.3.1 (`src/freemyid/__init__.py`). The formula URL names `freemyid-0.3.1.tar.gz`. The published Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09 (`site_src/data/release.yaml`). That record is the Windows installer only. It does not list Homebrew. 0.2.0 is not the current version.

Hashes in the recipe are placeholders until the release hashes are filled in. `sha256` is the text `REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING`. Dependency `resource` blocks are missing, so those checksums are not filled in either. Do not invent hashes. Do not replace a placeholder with a real hash. In-house release tooling fills them later. This note did not.

## What else is in the formula

- It depends on `python@3.12`, and on `rust` at build time, because some Python packages may build from source.
- The test block runs `freemyid --help` and looks for the word `Usage`. Not run.
- A future tap would be a separate repository. Users would then run `brew tap` and `brew install`. That tap does not exist in this tree. Not sure of the final tap name.

## How a maintainer would verify it

Read the file. Do not edit the hash.

1. Open `src/freemyid/__init__.py` and confirm `__version__` is `0.3.1`.
2. Open `freemyid.rb` and confirm the URL names `freemyid-0.3.1.tar.gz`.
3. Open `site_src/data/release.yaml` and confirm the Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09.
4. Confirm `sha256` is still `REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING`, and that there are still no `resource` blocks. Leave them.

After release tooling has put in the real source checksum and the dependency `resource` blocks, and not before, check with Homebrew. These commands were not run here:

```
cd distro/homebrew
brew install --build-from-source ./freemyid.rb
brew test freemyid
freemyid --help
brew uninstall freemyid
```

`brew audit --strict --new --formula freemyid` is the stricter check, once the formula lives in a tap. Newer Homebrew may refuse a formula path outside a tap. If so, copy the formula into a local tap made with `brew tap-new` and install from there. Not sure that extra step is required. Do not type a hash in by hand. `brew update-python-resources` needs network access; that is release tooling.

Status: **coming**.
