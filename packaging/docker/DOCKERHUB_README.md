# Free My ID

Free My ID helps you ask data-broker and people-search sites to remove your personal listings. It runs on your own computer and keeps your information there. You never need an account to use it.

This is an early release. Expect rough edges, and please start in practice mode, which sends nothing.

- Website, guides and the Windows installer: https://freemyid.org
- Source code and issues: https://github.com/FreeMyID/freemyid
- Security contact: https://freemyid.org/.well-known/security.txt

## Quick start

    docker run --rm docker.io/freemyid/freemyid --help
    docker run --rm docker.io/freemyid/freemyid doctor

The image runs as a normal user, not root. Keep your data in a mounted volume and pass your passphrase through a file, not on the command line. A ready-to-edit compose file with a fake example profile is in the repository under `packaging/docker/`.

## Tags

- `vX.Y.Z`: a specific release.
- `latest`: the newest full release (pre-releases never move it).

Every image is signed with Sigstore cosign and carries an SBOM. The same image is also published at `ghcr.io/freemyid/freemyid`.
