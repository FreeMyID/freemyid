class Freemyid < Formula
  include Language::Python::Virtualenv

  desc "Local-first personal data broker opt-out tool with scheduled re-checks"
  homepage "https://freemyid.org"
  # Version matches pyproject.toml ([project] version). Release tooling updates url and sha256.
  url "https://files.pythonhosted.org/packages/source/f/freemyid/freemyid-0.3.1.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING"
  license "AGPL-3.0-or-later"

  depends_on "rust" => :build # cryptography and pydantic-core may build from source
  depends_on "python@3.12"

  # RESOURCE BLOCKS: release tooling generates the dependency `resource` stanzas
  # (url + sha256 for every transitive dependency) with:
  #   brew update-python-resources freemyid
  # They were not written by hand because that needs network access.

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Usage", shell_output("#{bin}/freemyid --help")
  end
end
